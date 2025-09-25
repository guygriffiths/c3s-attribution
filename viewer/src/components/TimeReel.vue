<script setup lang="ts">
import scssVars from '@/assets/styles/scssVars.module.scss'
import { useLabels } from '@/lib/labels'
import {
	assignTimelinePositions,
	dayStr,
	monthsForYear,
	TOTAL_DAYS,
} from '@/lib/time-utils'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faBackward,
	faFastBackward,
	faFastForward,
	faForward,
	faPause,
	faPlay,
} from '@fortawesome/free-solid-svg-icons'
import * as d3 from 'd3'
import { addHours, differenceInDays, getDayOfYear, subHours } from 'date-fns'
import {
	computed,
	defineModel,
	onBeforeUnmount,
	onMounted,
	onUnmounted,
	PropType,
	ref,
	Ref,
	watch,
} from 'vue'

const $l = useLabels()

const props = defineProps({
	start: { type: Date, default: () => new Date(1970, 0, 1) },
	end: { type: Date, default: () => new Date(2024, 0, 1) },
	events: { type: Array<WeatherEvent>, default: () => [] as WeatherEvent[] },
	selectedEvent: { type: Object as () => WeatherEvent | null, default: null },
	mode: {
		type: String as PropType<TimeReelMode>,
		default: 'default',
	},
	showBars: { type: Boolean, default: true },
	colorForEvent: {
		type: Function as PropType<(event: ExtremeEvent) => string | null>,
		default: (event: ExtremeEvent) => event.color || null,
	},
})

const startYear = computed(() => props.start.getUTCFullYear())
const endYear = computed(() => props.end.getUTCFullYear())
const totalYears = computed(() => endYear.value - startYear.value + 1)
const years = computed(() =>
	Array.from({ length: totalYears.value }, (_, i) => startYear.value + i),
)
const showBars = computed(() => props.showBars && props.mode !== 'timeline')

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})
const selectedDay = computed(() => getDayOfYear(model.value))
const selectedYear = computed(() => model.value.getUTCFullYear())
const zoom = computed(() => props.mode === 'eventzoom')

const emits = defineEmits<{
	(event: 'eventSelected', id: string): void
}>()

////////////////////
// Time selection //
////////////////////
const setDate = (date: Date) => {
	if (
		date.getUTCFullYear() >= props.start.getUTCFullYear() &&
		date.getUTCFullYear() <= props.end.getUTCFullYear()
	) {
		model.value = date
	}
}
const scrollToYear = (year: number) => {
	if (container.value) {
		// Snap to top of specified year
		const yearsOffset = year - startYear.value - 1
		const scrollOffset = (yearsOffset + 0.5) * rowHeight.value
		container.value.scrollTo({
			top: scrollOffset,
			behavior: 'smooth',
		})
	}
}
const nextDay = () => {
	const newVal = addHours(model.value, 24)
	if (newVal.getUTCFullYear() <= endYear.value) {
		if (newVal.getUTCFullYear() !== model.value.getUTCFullYear()) {
			scrollToYear(newVal.getUTCFullYear())
		}
		model.value = newVal
	}
}
const prevDay = () => {
	const newVal = subHours(model.value, 24)
	if (newVal.getUTCFullYear() >= startYear.value) {
		if (newVal.getUTCFullYear() !== model.value.getUTCFullYear()) {
			scrollToYear(newVal.getUTCFullYear())
		}
		model.value = newVal
	}
}
const nextYear = () => {
	scrollToYear(selectedYear.value + 1)
}
const prevYear = () => {
	scrollToYear(selectedYear.value - 1)
}

const playing = ref(false)
const FPS = 15
const frameInterval = 1000 / FPS

const togglePlay = () => {
	playing.value = !playing.value
	if (playing.value) {
		let last = performance.now()

		const step = (ts: number) => {
			if (!playing.value) return

			if (ts - last >= frameInterval) {
				nextDay()
				last = ts
			}

			requestAnimationFrame(step)
		}

		requestAnimationFrame(step)
	}
}

////////////////////
// UI Interaction //
////////////////////
const timeReelRef = ref<HTMLDivElement | null>(null)
const needleRef = ref<HTMLDivElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const container = computed(() => timeReelRef.value?.querySelector('.scroller'))
const rowHeight = ref(128)
const updateRowHeight = () => {
	const parentHeight = timeReelRef.value?.clientHeight || 0
	rowHeight.value = parentHeight > 0 ? parentHeight / rowsToShow.value : 128
}
watch(
	() => props.mode,
	() => false && updateRowHeight(),
	{ immediate: false },
)

const oneRow = ref(false)
watch(oneRow, () => updateRowHeight())
const rowsToShow = computed(() => {
	if (oneRow.value) return 1
	switch (props.mode) {
		case 'timeline':
		case 'eventzoom':
			return 1
		case 'overview':
			return endYear.value - startYear.value + 1
		case 'default':
		default:
			return 2
	}
})

const maxSimultaneousEvents = computed(() => {
	return Math.max(3, Math.max(...dayCounts.value))
})

const populateEvents = () => {
	years.value.forEach((year) => {
		const { events: eventsForYear, maxEvents } = assignTimelinePositions(
			props.events,
			year,
		)

		eventsByYear.value.set(year, eventsForYear)
	})
}

const eventIsSelected = (event: { id: string }) =>
	event.id === props.selectedEvent?.id
const eventHeight = computed(() => 1.0 / maxSimultaneousEvents.value)

const isDragging = ref(false)
const dragMode = ref<'horizontal' | 'vertical' | null>(null)
let startX = 0
let startY = 0
let startDate: Date = new Date(model.value)
let startMs = 0

const startDrag = (event: MouseEvent) => {
	isDragging.value = true
	dragMode.value = null

	startX = event.clientX
	startY = event.clientY
	startMs = performance.now()
	startDate = model.value
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', endDrag)
}

const endDrag = (event: MouseEvent) => {
	isDragging.value = false
	dragMode.value = null
	const time = performance.now() - startMs
	if (time < 200 && Math.abs(event.clientX - startX) < 5) {
		// This was a click, not a drag
		console.log('click detected')
		const container = containerRef.value
		const xOffset =
			event.clientX - (container?.getBoundingClientRect().left || 0)
		const percentage = xOffset / (container?.clientWidth || 1)
		const totalDays = selectedYear.value % 4 === 0 ? 365 : 364
		const dayFromStart = Math.floor(
			1 + Math.max(0, Math.min(1, percentage)) * totalDays,
		)
		const newDate = new Date(Date.UTC(selectedYear.value, 0, dayFromStart))
		setDate(
			new Date(
				Date.UTC(newDate.getFullYear(), newDate.getMonth(), newDate.getDate()),
			),
		)
	}

	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', endDrag)
}

const handleDrag = (event: MouseEvent) => {
	const dx = event.clientX - startX
	const dy = event.clientY - startY

	if (!dragMode.value) {
		if (Math.abs(dx) > Math.abs(dy)) dragMode.value = 'horizontal'
		else if (Math.abs(dy) > Math.abs(dx)) dragMode.value = 'vertical'
		else return
	}

	if (dragMode.value === 'horizontal') {
		const container = containerRef.value
		if (container) {
			const rect = container.getBoundingClientRect()
			// const offsetX = event.clientX - rect.left
			// const percentage = offsetX / rect.width
			const totalDays = selectedYear.value % 4 === 0 ? 365 : 364

			const pixelsPerDay = rect.width / totalDays
			const daysMoved = Math.round(dx / pixelsPerDay)

			if (!props.selectedEvent) {
				// addHours will respect DST, addDays won't
				const newDate = addHours(startDate, 24 * daysMoved)
				if (newDate.getFullYear() === selectedYear.value) {
					setDate(newDate)
				} else if (newDate.getFullYear() < selectedYear.value) {
					setDate(new Date(Date.UTC(selectedYear.value, 0, 1)))
				} else if (newDate.getFullYear() > selectedYear.value) {
					setDate(new Date(Date.UTC(selectedYear.value, 11, 31)))
				}
			} else {
				console.log('dragging does not work with selected event yet')
				// const eventStart = getDayOfYear(props.selectedEvent.times[0])
				// const eventEnd = getDayOfYear(
				// 	props.selectedEvent.times[props.selectedEvent.times.length - 1],
				// )
				// const dragDays = eventEnd - eventStart + 2

				// const dayFromStart = Math.floor(
				// 	1 + Math.max(0, Math.min(1, percentage)) * dragDays,
				// )
				// const tempDate = setDayOfYear(
				// 	new Date(Date.UTC(selectedYear.value, 0, 1)),
				// 	dayFromStart + eventStart - 1,
				// )

				// setDate(
				// 	new Date(
				// 		Date.UTC(
				// 			tempDate.getFullYear(),
				// 			tempDate.getMonth(),
				// 			tempDate.getDate(),
				// 		),
				// 	),
				// )
			}
		}
	} else if (dragMode.value === 'vertical') {
		// yOffset.value -= dy
		// yOffset.value = Math.max(0, yOffset.value)
		// if (dy > 0) {
		// 	prevYear()
		// } else {
		// 	nextYear()
		// }
		// startY = event.clientY
	}
}

const eventClicked = (event: WeatherEvent) => {
	emits('eventSelected', event.id)
}
const needleOffset = computed(() => {
	if (props.mode === 'default' || props.mode === 'overview') {
		const offset = (selectedDay.value / TOTAL_DAYS) * 100
		return Math.max(Math.min(offset, 100), 0)
	} else if (props.mode === 'timeline') {
	} else if (props.mode === 'eventzoom') {
		// In zoom mode, we want to center the needle on the selected event
		if (props.selectedEvent) {
			const eventStart = getDayOfYear(props.selectedEvent.times[0])
			const selectedDay = getDayOfYear(model.value)
			const eventEnd = getDayOfYear(
				props.selectedEvent.times[props.selectedEvent.times.length - 1],
			)
			const totalZoomedDays = eventEnd - eventStart + 2
			const offset = selectedDay - eventStart + 1
			return (offset / totalZoomedDays) * 100
		}
	} else {
		// Fallback, shouldn't get here
		return ((selectedDay.value / TOTAL_DAYS) * 100).toFixed(2)
	}
})

const positionY = (y: number) => {
	// return 0.5 * y * eventHeight.value
	if (y % 2 === 0) {
		return -0.5 * eventHeight.value * y
	} else {
		return 0.5 * eventHeight.value * (y + 1)
	}
}

onMounted(() => {
	populateEvents()
	const handleKey = (e: KeyboardEvent) => {
		// TODO Should all of this go in a global key handler? Perhaps not, since people use arrow keys on maps?
		if (e.key === 'PageUp') prevYear()
		else if (e.key === 'PageDown') nextYear()
		else if (e.key === 'ArrowLeft') prevDay()
		else if (e.key === 'ArrowRight') nextDay()
		// else if (e.key === 'ArrowUp') prevYear()
		// else if (e.key === 'ArrowDown') nextYear()
		// else if (e.key === 'R') nextYear()
		else if (e.key === 'Home') setDate(new Date(props.start.getTime()))
		else if (e.key === 'End') setDate(new Date(props.end.getTime()))
	}
	window.addEventListener('keydown', handleKey)

	if (model.value > props.end) {
		model.value = new Date(props.end.getTime())
	} else if (model.value < props.start) {
		model.value = new Date(props.start.getTime())
	}

	updateRowHeight() // initial
	const ro = new ResizeObserver(updateRowHeight)
	if (timeReelRef.value) {
		ro.observe(timeReelRef.value)
		timeReelRef.value.focus()
	}

	onBeforeUnmount(() => {
		window.removeEventListener('keydown', handleKey)
	})
	onUnmounted(() => ro.disconnect())
})

const topRowHeight = computed(() => {
	return `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})
const bottomRowHeight = computed(() => {
	return `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})

const highlightRowHeight = computed(() => `calc(100% / ${rowsToShow.value})`)

const getAreaString = () => {
	// TODO cache the global one? How will we know
	const data: Array<{ x: number; y: number }> = dayCounts.value.map((d, i) => ({
		x: i,
		y: d,
	}))
	const yScale = d3
		.scaleLinear()
		.domain([0, 1.05 * maxSimultaneousEvents.value])
		.range([0, 0.5])
	const areaStr = d3
		.area<{ x: number; y: number }>()
		.x((d) => d.x)
		.y0((d) => -yScale(d.y))
		.y1((d) => yScale(d.y))
		.defined((d) => d.x >= 0 && d.x < dayCounts.value.length)
		.curve(d3.curveMonotoneX)(data! || [])
	return areaStr || ''
}

const scrollListener = () => {
	const scrollTop = container.value!.scrollTop
	const rowsDown = scrollTop / rowHeight.value
	const newYear = Math.round(startYear.value + rowsDown)
	const newDate = new Date(Date.UTC(newYear, 0, getDayOfYear(model.value)))
	setDate(newDate)
}

const eventsByYear = ref(new Map<number, WeatherEvent[]>())
const dayCounts = ref<number[]>([])
watch(
	() => props.events,
	() => {
		// console.log('events changed, recalculating positions', props.events)
		const byYear = new Map<number, WeatherEvent[]>()
		for (const event of props.events) {
			const startYear = event.times[0]?.getUTCFullYear()
			const endYear = event.times[event.times.length - 1]?.getUTCFullYear()
			if (startYear === endYear) {
				if (!byYear.has(startYear)) byYear.set(startYear, [])
				byYear.get(startYear)!.push(event)
			} else {
				for (let y = startYear; y <= endYear; y++) {
					if (!byYear.has(y)) byYear.set(y, [])
					byYear.get(y)!.push(event)
				}
			}
		}
		eventsByYear.value = byYear
		populateEvents()

		const totalDays = differenceInDays(props.end, props.start) + 1
		const counts = new Array(totalDays).fill(0)
		props.events.forEach((event: WeatherEvent) => {
			event?.times.forEach((time) => {
				const daysFromStart = differenceInDays(time, props.start)
				counts[daysFromStart] += 1
			})
		})
		dayCounts.value = counts

		const newD = getAreaString()
		const animTime = parseFloat(scssVars.animTime.replaceAll('s', '')) * 1000
		if (model.value > props.end) {
			model.value = new Date(props.end.getTime())
		} else if (model.value < props.start) {
			model.value = new Date(props.start.getTime())
		}
		for (const year of years.value) {
			d3.select(`#events-line-${year}`)
				.transition()
				.duration(50)
				.attr('d', newD)
			assignTimelinePositions(props.events, year)
		}
		// console.log('updated events by year', eventsByYear.value)

		if (container.value) {
			const yearsOffset = selectedYear.value - startYear.value
			const scrollOffset = 0.5 * (yearsOffset * 2 - 1)
			container.value.scrollTo({
				top: scrollOffset * rowHeight.value,
			})
		}
	},
	{ immediate: true, deep: false },
)

const viewportTransform = computed(() => {
	if (props.selectedEvent && props.mode === 'eventzoom') {
		const eventStart = getDayOfYear(props.selectedEvent.times[0])
		const eventEnd = getDayOfYear(
			props.selectedEvent.times[props.selectedEvent.times.length - 1],
		)
		const nDays = eventEnd - eventStart + 2
		const scale = 366 / nDays

		return `scale(${scale}, 1) `
	} else {
		return 'translate(0, 0)'
	}
})

const lineTransform = computed(() => {
	return (year: number): string =>
		props.mode == 'timeline'
			? `translate(0, ${-year + selectedYear.value}) scale(${1.0 / years.value.length}, 1)`
			: `translate(${-differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)},0)`
})

const monthsTransform = computed(() => {
	return (year: number): string =>
		`scale(${1.0 / years.value.length}, 1) translate(${differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)}, ${-year + selectedYear.value}) `
})

const yearTransform = computed(() => {
	return (year: number): string =>
		`translate(0, ${year - startYear.value + 0.5})`
})

const lineOpacity = computed(() => {
	return (year: number): number => {
		if (props.mode === 'timeline') {
			return year === selectedYear.value ? 1.0 : 0.1
		}
		return 1
		// else if ((props.showBars || zoom) && year === selectedYear.value)
		// 	return 0.25
		// else return 1.0
	}
})

const svgStyle = computed(() => {
	return ''
	const yOffset = (rowsToShow.value - 1) * 0.5 * rowHeight.value
	const height = totalYears.value * rowHeight.value
	return `transform: translateY(${yOffset}px); height: ${height}px;`
})
</script>

<template>
	<div class="time-reel" ref="timeReelRef">
		<div
			class="controls"
			:class="{
				hidden: !(props.mode === 'default' || props.mode === 'eventzoom'),
				zoom: props.mode === 'eventzoom',
			}"
		>
			<div class="info">
				{{ dayStr(selectedDay, selectedYear) }}
			</div>
			<div class="buttons">
				<!-- <button @click="oneRow = !oneRow">Toggle Rows</button> -->
				<button @click="prevYear" :disabled="selectedYear <= startYear">
					<span class="sr-only">{{ $l.prevYear }}</span>
					<font-awesome-icon :icon="faFastBackward" />
				</button>
				<button
					@click.stop="prevDay"
					:disabled="selectedYear <= startYear && selectedDay <= 1"
				>
					<span class="sr-only">{{ $l.prevDay }}</span>
					<font-awesome-icon :icon="faBackward" />
				</button>
				<button @click="togglePlay">
					<span class="sr-only">{{ $l.play }}</span>
					<font-awesome-icon :icon="playing ? faPause : faPlay" />
				</button>
				<button
					@click="nextDay"
					:disabled="selectedYear >= endYear && selectedDay >= 365"
				>
					<span class="sr-only">{{ $l.nextDay }}</span>
					<font-awesome-icon :icon="faForward" />
				</button>
				<button @click="nextYear" :disabled="selectedYear >= endYear">
					<span class="sr-only">{{ $l.nextYear }}</span>
					<font-awesome-icon :icon="faFastForward" />
				</button>
			</div>
		</div>
		<div
			class="scroller"
			@scroll="scrollListener"
			@mousedown="startDrag"
			@click="console.log('click')"
			@prevent.default
			:class="{
				timeline: props.mode === 'timeline',
				eventzoom: props.mode === 'eventzoom',
			}"
		>
			<div
				class="scrollee"
				:style="`margin: ${(rowsToShow - 1) * 0.5 * rowHeight}px 0;`"
			>
				<div
					v-for="year in years"
					:key="year"
					:style="`height: ${rowHeight}px;`"
					class="year"
					:class="{
						timeline: mode === 'timeline',
						highlight: year === selectedYear,
						odd: year % 2 === 1,
					}"
				>
					<h1
						class="label"
						:style="`opacity: ${props.mode === 'timeline' ? 0 : 1}`"
					>
						{{ year }}
					</h1>
				</div>
				<div class="clipper">
					<svg
						class="events-svg"
						ref="containerRef"
						xmlns="http://www.w3.org/2000/svg"
						:viewBox="`0 0 366 ${endYear - startYear + 1}`"
						:style="svgStyle"
						preserveAspectRatio="none"
					>
						<g :transform="viewportTransform">
							<g
								v-for="year in years"
								:key="year"
								class="year-group"
								:transform="yearTransform(year)"
							>
								<path
									:id="`events-line-${year}`"
									class="event-line"
									d=""
									vector-effect="non-scaling-stroke"
									:stroke-width="3"
									:transform="lineTransform(year)"
									:opacity="lineOpacity(year)"
								/>
								<transition-group tag="g" name="daily-event-fx" v-if="showBars">
									<rect
										v-for="event in eventsByYear
											.get(year)
											?.filter(() => year == selectedYear) || []"
										class="event-bar"
										:data-id="event.id"
										:key="event.id"
										:x="event.startX! - 0.5"
										:width="event.endX! - event.startX! + 1"
										:y="
											eventIsSelected(event)
												? -0.5
												: positionY(event.y!) - 0.5 * eventHeight
										"
										:height="
											eventIsSelected(event)
												? 2 * eventHeight
												: 0.9 * eventHeight
										"
										:fill="
											colorForEvent(event as any as ExtremeEvent) || '#ff0000'
										"
										:class="{
											selected: eventIsSelected(event),
											unselected:
												!eventIsSelected(event) && props.selectedEvent !== null,
										}"
										:opacity="
											eventIsSelected(event) ||
											props.mode === 'eventzoom' ||
											year !== selectedYear
												? 0.9
												: 1
										"
										@click="eventClicked(event)"
									/>
								</transition-group>
								<rect
									v-for="(month, i) in monthsForYear(
										year,
										props.mode === 'default' || props.mode === 'overview',
										$l,
									)"
									:transform="
										props.mode === 'timeline'
											? monthsTransform(year)
											: 'translate(0,0)'
									"
									:key="`${year}${i}`"
									class="background"
									:class="{ oddyear: year % 2 === 0 }"
									:x="month.startX"
									:width="month.length"
									:y="-0.5"
									:height="1"
									:fill="month.color"
									:opacity="zoom ? 0 : 1"
								/>
							</g>
						</g>
					</svg>
				</div>
			</div>
		</div>

		<div class="year-highlights" @prevent.default>
			<div
				class="highlight-row fade-top"
				:class="{ examining: props.mode === 'default' }"
				:style="`height: ${topRowHeight};`"
			></div>
			<div
				class="highlight-row highlight"
				:style="`height: ${highlightRowHeight};`"
				:class="{ examining: props.mode === 'default' }"
			>
				<div
					class="needle"
					ref="needleRef"
					v-if="props.mode === 'default' || props.mode === 'eventzoom'"
					:style="`left: ${needleOffset}%; pointer-events: none;`"
				>
					<div class="line" />
					<div class="label" :class="{ hidden: !isDragging }">
						<p>{{ dayStr(selectedDay, selectedYear) }}</p>
					</div>
				</div>
				<div class="month-labels" v-if="!zoom && props.mode !== 'timeline'">
					<p v-show="!zoom" class="jan">{{ $l.months.jan }}</p>
					<p v-show="!zoom" class="feb">{{ $l.months.feb }}</p>
					<p v-show="!zoom" class="mar">{{ $l.months.mar }}</p>
					<p v-show="!zoom" class="apr">{{ $l.months.apr }}</p>
					<p v-show="!zoom" class="may">{{ $l.months.may }}</p>
					<p v-show="!zoom" class="jun">{{ $l.months.jun }}</p>
					<p v-show="!zoom" class="jul">{{ $l.months.jul }}</p>
					<p v-show="!zoom" class="aug">{{ $l.months.aug }}</p>
					<p v-show="!zoom" class="sep">{{ $l.months.sep }}</p>
					<p v-show="!zoom" class="oct">{{ $l.months.oct }}</p>
					<p v-show="!zoom" class="nov">{{ $l.months.nov }}</p>
					<p v-show="!zoom" class="dec">{{ $l.months.dec }}</p>
				</div>
			</div>
			<div
				class="highlight-row fade-bottom"
				:class="{ examining: props.mode === 'default' }"
				:style="`height: ${bottomRowHeight};`"
			></div>
		</div>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

// $fitTime: $animTime * 0.25;
// $zoomTime: 3 * $animTime * 0.25;

.time-reel {
	// position: relative;
	// overflow-y: scroll;
	height: 100%;

	.controls {
		height: 2rem;
		position: absolute;
		top: -1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 3;
		background-color: rgba(255, 255, 255, 0.8);
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		user-select: none;

		button {
			color: white;
			width: 3rem;
		}

		&.hidden {
			display: none;
		}

		&.zoom {
			opacity: 0.5;
			display: none;
		}
	}

	.scroller {
		width: 100%;
		height: 100%;
		overflow-y: auto;
		position: relative;
		scroll-snap-type: y mandatory;
		display: block;

		&.timeline {
			overflow-y: hidden;
		}

		.scrollee {
			position: relative;
			width: 100%;
			background-color: aqua;

			.clipper {
				position: absolute;
				top: 0;
				bottom: 0;
				width: 100%;
				height: 100%;
				overflow: hidden;
				background-color: rgba(238, 130, 238, 0.433);
				background-color: transparent;

				.events-svg {
					position: absolute;
					transition: all $animTime ease-in-out;
					top: 0;
					left: 0;
					height: 100%;
					background-color: transparent;
					width: 100%;
					margin: 0;
					padding: 0;
					.background {
						transition: all calc(1 * $animTime) ease-in-out;
						&.oddyear {
							background-color: rgba($c3sblue, 0.1);
						}
					}
				}
			}

			.year {
				// border: 2px solid red;
				transition:
					all $animTime ease-in-out,
					height 0s linear;

				scroll-snap-align: center;
				background-color: $panelBg;
				display: flex;
				flex-direction: row;
				align-items: flex-end;
				justify-content: flex-end;
				width: 100%;
				position: relative;

				.label {
					font-size: 1.5rem;
					color: $c3sblue;
					margin: 0;
					padding: 0.5rem 0.5rem;
					transition: opacity 0s linear;
				}
			}
		}
	}

	.event-line {
		stroke: $c3sblue;
		// stroke-width: 0.025;
		fill: $c3sblue;
		fill-opacity: 0.25;
		pointer-events: none;
		// transition: all calc(1.0 * $animTime) ease-in-out calc(1.0 * $animTime);
		transition: all calc(1 * $animTime) ease-in-out;
	}

	.timeline {
		.event-line {
			stroke: $c3sred;
			fill: $c3sred;
			transition: all calc(1 * $animTime) ease-in-out;
		}
	}

	.year-highlights {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		// display: flex;
		// flex-direction: column;
		// justify-content: space-between;
		display: block;
		z-index: 2;
		pointer-events: none;
		transition: all $animTime ease-in-out;
		border: none;

		$fadeColor: #aaaaaa;

		.highlight-row {
			transition: all $animTime ease-in-out;
			overflow: hidden;

			&.fade-top {
				pointer-events: none;
				background: linear-gradient(
					to top,
					rgba($fadeColor, 0.3),
					rgba($fadeColor, 1)
				);
				&.exploring {
					background: linear-gradient(
						to top,
						rgba($fadeColor, 0.1),
						rgba($fadeColor, 0.5)
					);
				}
			}
			&.fade-bottom {
				pointer-events: none;
				background: linear-gradient(
					to bottom,
					rgba($fadeColor, 0.3),
					rgba($fadeColor, 1)
				);
				&.exploring {
					background: linear-gradient(
						to top,
						rgba($fadeColor, 0.5),
						rgba($fadeColor, 0.1)
					);
				}
			}
			&.highlight {
				position: relative;
				width: 100%;
				display: flex;
				flex-direction: row;
				align-items: stretch;
				color: #aaaaaa;
				box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
				&.exploring {
					box-shadow: 0 0 5px rgba($fadeColor, 0.5);
				}
				pointer-events: none;

				.needle {
					pointer-events: none;
					display: block;
					position: absolute;
					top: 0;
					left: 0;
					margin-left: -2px;
					background-color: transparent;
					transform-origin: left center;
					width: 1px;
					height: 100%;
					box-sizing: border-box;
					cursor: ew-resize;
					border-top: 7px solid $c3sred;
					border-right: 7px solid transparent;
					border-left: 7px solid transparent;
					border-bottom: none;
					transform: translateX(-50%);

					.line {
						position: absolute;
						width: 1px;
						height: 100%;
						background-color: $c3sred;
					}

					.label {
						opacity: 1;
						position: absolute;
						top: 0;
						left: 0;
						transform: translate(-50%, -120%);
						background-color: white;
						border-radius: 4px;
						padding: 0.25rem;
						box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
						z-index: 1;
						pointer-events: none;
						user-select: none;
						transition: opacity $animTime ease-in-out;

						&.hidden {
							opacity: 0;
						}

						p {
							margin: 0;
							font-size: 0.75rem;
							color: #333333;
							text-align: center;
						}
					}
				}
				.month-labels {
					flex: 0 0 100%;
					pointer-events: none;
					user-select: none;
					display: flex;
					flex-direction: row;
					p {
						pointer-events: none;
						user-select: none;
						flex-grow: 1;
						text-align: center;
						margin: 0;
						display: flex;
						justify-content: center;
						align-items: flex-end;
					}

					.jan {
						flex-basis: 31fr;
					}
					.feb {
						flex-basis: 28fr;
					}
					.mar {
						flex-basis: 31fr;
					}
					.apr {
						flex-basis: 30fr;
					}
					.may {
						flex-basis: 31fr;
					}
					.jun {
						flex-basis: 30fr;
					}
					.jul {
						flex-basis: 31fr;
					}
					.aug {
						flex-basis: 31fr;
					}
					.sep {
						flex-basis: 30fr;
					}
					.oct {
						flex-basis: 31fr;
					}
					.nov {
						flex-basis: 30fr;
					}
					.dec {
						flex-basis: 31fr;
					}
				}
			}
		}
	}

	.events-svg {
		.year-group {
			transition: all $animTime ease-in-out;
		}

		.background {
			pointer-events: none;
			stroke: 0;
		}

		.event-bar {
			cursor: pointer;

			transition:
				all $settleTime ease-in-out $animTime,
				opacity $animTime ease-in-out;

			&.selected {
				transition:
					all $settleTime ease-in-out $animTime,
					opacity 0s ease-in-out calc($animTime + $settleTime);
			}

			&.unselected {
				transition:
					all $settleTime ease-in-out,
					opacity 0.5 ease-in-out;
				// TODO looks iffy
				opacity: 1;
			}
		}
		.day-box {
			stroke-width: 2;
			opacity: 1;
		}

		.daily-event-fx-enter-from {
			opacity: 0;
			transition: opacity $animTime ease-in-out;
		}
		.daily-event-fx-enter-to {
			opacity: 1;
		}

		.daily-event-fx-leave-from {
			opacity: 1;
			transition: opacity $animTime ease-in-out;
		}
		.daily-event-fx-leave-to {
			opacity: 0;
		}

		.selected-event-fx-enter-from {
			opacity: 0;
			stroke-width: 0;
		}
		.selected-event-fx-enter-to {
			opacity: 1;
			stroke-width: 2;
		}
		.selected-event-fx-enter-active {
			transition:
				stroke-width 0s ease-out calc($animTime + $settleTime + var(--i) * 20ms),
				opacity 0s ease-out calc($animTime + $settleTime);
		}

		.selected-event-fx-leave-from {
			opacity: 1;
			stroke-width: 2;
		}
		.selected-event-fx-leave-to {
			opacity: 0;
			stroke-width: 0;
		}
		.selected-event-fx-leave-active {
			// transition:
			// 	stroke-width $animTime ease calc(var(--i) * 20ms) $settleTime,
			// 	opacity $animTime ease-in-out $settleTime;
			transition:
				transform 0s ease-in-out,
				stroke-width 0s ease-out calc(var(--i) * 20ms),
				opacity 0s ease-out $settleTime;
		}
	}
}
</style>
