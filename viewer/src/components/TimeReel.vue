<script setup lang="ts">
import scssVars from '@/assets/styles/scssVars.module.scss'
import { useLabels } from '@/lib/labels'
import {
	getEventBoxes,
	dayStr,
	monthsForYear,
	TOTAL_DAYS,
} from '@/lib/time-utils'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faBackward,
	faBackwardStep,
	faF,
	faFastBackward,
	faFastForward,
	faForward,
	faForwardStep,
	faPause,
	faPlay,
} from '@fortawesome/free-solid-svg-icons'
import * as d3 from 'd3'
import {
	addHours,
	differenceInDays,
	getDayOfYear,
	lastDayOfDecade,
	setDayOfYear,
	subHours,
} from 'date-fns'
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
	events: { type: Array<ExtremeEvent>, default: () => [] },
	selectedEvent: {
		type: Object as () => ExtremeEventFull | null,
		default: null,
	},
	mode: {
		type: String as PropType<TimeReelMode>,
		default: 'default',
	},
	showBars: { type: Boolean, default: true },
	hot: { type: Boolean, default: true },
	cold: { type: Boolean, default: true },
	colorForEvent: {
		type: Function as PropType<(event: ExtremeEvent) => string | null>,
		default: (event: ExtremeEvent) => event.color || null,
	},
	valueExtractor: {
		type: Function as PropType<(event: ExtremeEvent) => number>,
		default: (event: ExtremeEvent) => event.max_value || 0,
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
const startOfYear = () => {
	setDate(new Date(Date.UTC(selectedYear.value, 0, 1)))
}
const endOfYear = () => {
	setDate(new Date(Date.UTC(selectedYear.value, 11, 31)))
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
watch(rowsToShow, () => updateRowHeight())

const maxSimultaneousEvents = computed(() => {
	return Math.max(3, ...hwDayCounts.value, ...cwDayCounts.value)
})

const eventIsSelected = (event: { id: string }) =>
	event.id === props.selectedEvent?.id
const eventHeight = computed(() => 1.0 / maxSimultaneousEvents.value)

const isDragging = ref(false)
const dragMode = ref<'horizontal' | 'vertical' | null>(null)
let startX = 0
let startY = 0
let startDate: Date = new Date(model.value)
let startMs = 0

const localNeedleOffset = ref(null as number | null)
const startDrag = (event: MouseEvent) => {
	dragMode.value = null

	startX = event.clientX
	startY = event.clientY
	startMs = performance.now()
	startDate = model.value
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', endDrag)

	if (props.mode === 'eventzoom') {
		localNeedleOffset.value = 0
	} else {
		localNeedleOffset.value = null
	}
}

const endDrag = (event: MouseEvent) => {
	isDragging.value = false
	dragMode.value = null
	localNeedleOffset.value = null
	const time = performance.now() - startMs
	if (time < 200 && Math.abs(event.clientX - startX) < 5) {
		// This was a click, not a drag
		console.log('click detected')

		const container = containerRef.value
		const xOffset =
			event.clientX - (container?.getBoundingClientRect().left || 0)
		const percentage = xOffset / (container?.clientWidth || 1)
		if (props.mode === 'eventzoom') {
			if (!props.selectedEvent) return
			const eventStart = getDayOfYear(props.selectedEvent.times[0])
			const eventEnd = getDayOfYear(
				props.selectedEvent.times[props.selectedEvent.times.length - 1],
			)
			const totalZoomedDays = (eventEnd - eventStart) * xScaleFactor.value

			const dayFromStart = Math.floor(
				1 + Math.max(0, Math.min(1, percentage)) * totalZoomedDays,
			)
			const newDate = setDayOfYear(
				new Date(Date.UTC(selectedYear.value, 0, 1)),
				dayFromStart + eventStart - 1,
			)
			// Only set the date if it has changed, otherwise it slows things down unnecessarily
			if (differenceInDays(newDate, model.value) !== 0) {
				setDate(
					new Date(
						Date.UTC(
							newDate.getFullYear(),
							newDate.getMonth(),
							newDate.getDate(),
						),
					),
				)
			}
		} else {
			const totalDays = selectedYear.value % 4 === 0 ? 365 : 364
			const dayFromStart = Math.floor(
				1 + Math.max(0, Math.min(1, percentage)) * totalDays,
			)
			const newDate = new Date(Date.UTC(selectedYear.value, 0, dayFromStart))
			setDate(
				new Date(
					Date.UTC(
						newDate.getFullYear(),
						newDate.getMonth(),
						newDate.getDate(),
					),
				),
			)
		}
	}

	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', endDrag)
}

const handleDrag = (event: MouseEvent) => {
	isDragging.value = true
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
			if (props.mode !== 'eventzoom') {
				const rect = container.getBoundingClientRect()
				const totalDays = selectedYear.value % 4 === 0 ? 365 : 364
				const pixelsPerDay = rect.width / totalDays
				const daysMoved = Math.round(dx / pixelsPerDay)

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
				const rect = container.getBoundingClientRect()
				const totalDays = props.selectedEvent
					? differenceInDays(
							props.selectedEvent.times[props.selectedEvent.times.length - 1],
							props.selectedEvent.times[0],
						) * xScaleFactor.value
					: 365
				const pixelsPerDay = rect.width / totalDays
				const daysMoved = Math.round(dx / pixelsPerDay)
				localNeedleOffset.value = dx / pixelsPerDay - daysMoved

				// No need to set anything and trigger a re-render if we haven't actually changed the day
				if (daysMoved === 0) return
				// addHours will respect DST, addDays won't
				const newDate = addHours(startDate, 24 * daysMoved)
				if (newDate.getFullYear() === selectedYear.value) {
					setDate(newDate)
				} else if (newDate.getFullYear() < selectedYear.value) {
					setDate(new Date(Date.UTC(selectedYear.value, 0, 1)))
				} else if (newDate.getFullYear() > selectedYear.value) {
					setDate(new Date(Date.UTC(selectedYear.value, 11, 31)))
				}
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

const eventClicked = (id: string) => {
	emits('eventSelected', id)
}

const needleOffset = computed(() => {
	if (props.mode === 'default' || props.mode === 'overview') {
		const offset = (selectedDay.value / TOTAL_DAYS) * 100 - 0.5
		return Math.max(Math.min(offset, 100), 0)
	} else if (props.mode === 'timeline') {
		const totalDays = differenceInDays(props.end, props.start) + 1
		const daysFromStart = differenceInDays(model.value, props.start) + 1
		const offset = (daysFromStart / totalDays) * 100 - 0.5
		return Math.max(Math.min(offset, 100), 0)
	} else if (props.mode === 'eventzoom') {
		if (props.selectedEvent) {
			const eventStart = getDayOfYear(props.selectedEvent.times[0])
			const selectedDay = getDayOfYear(model.value)
			const eventEnd = getDayOfYear(
				props.selectedEvent.times[props.selectedEvent.times.length - 1],
			)
			const totalZoomedDays = (eventEnd - eventStart) * xScaleFactor.value
			const offset = selectedDay - eventStart + 1
			if (localNeedleOffset.value !== null) {
				return Math.max(
					Math.min(
						((offset + localNeedleOffset.value) / totalZoomedDays) * 100,
						100,
					),
					0,
				)
			}
			return (offset / totalZoomedDays) * 100
		}
	} else {
		// Fallback, shouldn't get here
		return (selectedDay.value / TOTAL_DAYS) * 100
	}
})

const eventBoxesForYear = ref<Record<number, EventBox[]>>({})
const positionY = (y: number, eventType: 'hot' | 'cold') => {
	if (props.hot && props.cold) {
		return (0.5 + y) * 0.5 * eventHeight.value * (eventType === 'hot' ? -1 : 1)
	} else {
		if (y % 2 !== 0) {
			return 0.5 * (y - 1) * eventHeight.value
		} else {
			return -0.5 * (y + 2) * eventHeight.value
		}
	}
}

onMounted(() => {
	for (let year of years.value) {
		const res = getEventBoxes(props.events, year, props.hot && props.cold)
		eventBoxesForYear.value[year] = res.events
	}
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
	return props.mode === 'overview'
		? '0'
		: `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})
const bottomRowHeight = computed(() => {
	return props.mode === 'overview'
		? '0'
		: `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})

const highlightRowHeight = computed(() =>
	props.mode === 'overview' ? '100%' : `calc(100% / ${rowsToShow.value})`,
)

const getAreaString = () => {
	const data: Array<{ x: number; y0: number; y1: number }> = props.hot
		? props.cold
			? // Hot and cold events
				hwDayCounts.value.map((d, i) => ({
					x: i,
					y0: cwDayCounts.value[i],
					y1: d,
				}))
			: // Hot events only
				hwDayCounts.value.map((d, i) => ({
					x: i,
					y0: d,
					y1: d,
				}))
		: // Cold events only
			cwDayCounts.value.map((d, i) => ({
				x: i,
				y0: d,
				y1: d,
			}))

	const yScale = d3
		.scaleLinear()
		// .domain([0, 1.05 * maxSimultaneousEvents.value])
		.domain([
			Math.min(...data.map((d) => d.y0).concat(data.map((d) => d.y1))) || 0,
			Math.max(...data.map((d) => d.y0).concat(data.map((d) => d.y1))) || 1,
		])
		.range([0, 0.5])
	const areaStr = d3
		.area<{ x: number; y0: number; y1: number }>()
		.x((d) => d.x)
		.y0((d) => yScale(d.y0))
		.y1((d) => -yScale(d.y1))
		.defined((d) => d.x >= 0 && d.x < hwDayCounts.value.length)
		.curve(d3.curveMonotoneX)

	const ret: Record<number, string> = {}
	for (let year of years.value) {
		const startOfYear = Date.UTC(year, 0, 1) // Jan 1 UTC
		const endOfYear = Date.UTC(year + 1, 0, 1) // Jan 1 next year UTC

		const startIdx = Math.max(
			0,
			Math.floor(
				(startOfYear - props.start.getTime()) / (1000 * 60 * 60 * 24),
			) - 1,
		)
		const endIdx = Math.min(
			data.length,
			Math.floor((endOfYear - props.start.getTime()) / (1000 * 60 * 60 * 24)) +
				1,
		)

		// We add 2 invisible moves to ensure that the centre of the object's bounding box is always at y=0
		// That way when we apply a vertical gradient, it is always centered
		ret[year] =
			areaStr(data.slice(startIdx, endIdx)) + ` M0,${-2} L0,0 M0,${2} L0,0` ||
			''
	}
	return ret
}

const scrollListener = () => {
	const scrollTop = container.value!.scrollTop
	const rowsDown = scrollTop / rowHeight.value
	const newYear = Math.round(startYear.value + rowsDown)
	const newDate = new Date(Date.UTC(newYear, 0, getDayOfYear(model.value)))
	setDate(newDate)
}

const eventsForYear = computed(() => {
	return (year: number) =>
		props.events.filter(
			(e) =>
				e.times[0]?.getUTCFullYear() === year ||
				e.times[e.times.length - 1]?.getUTCFullYear() === year,
		)
})

const cwDayCounts = ref<number[]>([])
const hwDayCounts = ref<number[]>([])
watch(
	() => props.events,
	() => {
		for (let year of years.value) {
			const res = getEventBoxes(props.events, year, props.hot && props.cold)
			eventBoxesForYear.value[year] = res.events
		}

		const totalDays = differenceInDays(props.end, props.start) + 1
		const cwCounts = new Array(totalDays).fill(0)
		const hwCounts = new Array(totalDays).fill(0)
		// TODO - Allow the value to be something other than the event count
		// e.g. total duration, or average duration, or peak value, etc. Pass in a valueFunc prop, and if it's null, use count
		const cwValues = new Array(totalDays).fill(0)
		const hwValues = new Array(totalDays).fill(0)
		props.events.forEach((event) => {
			event?.times.forEach((time, i) => {
				const daysFromStart = differenceInDays(time, props.start)
				if (event.event_type === 'cold') {
					cwCounts[daysFromStart] += 1
					cwValues[daysFromStart] += event.duration || 0
				} else if (event.event_type === 'hot') {
					hwCounts[daysFromStart] += 1
					hwValues[daysFromStart] += event.duration || 0
				}
			})
		})
		cwDayCounts.value = cwCounts
		// .map((d, i) => cwValues[i] / d || 0)
		// .map((d) => (isNaN(d) ? 0 : d))
		hwDayCounts.value = hwCounts
		// .map((d, i) => hwValues[i] / d || 0)
		// .map((d) => (isNaN(d) ? 0 : d))

		const newD = getAreaString()

		for (const year of years.value) {
			d3.select(`#events-line-${year}`)
				.transition()
				.duration(500)
				.attr('d', newD[year])
		}

		if (container.value) {
			const yearsOffset = selectedYear.value - startYear.value
			const scrollOffset = 0.5 * (yearsOffset * 2 - 1)
			container.value.scrollTo({
				top: scrollOffset * rowHeight.value,
			})
			console.log('and scrolled to', selectedYear.value)
		}
	},
	{ immediate: true, deep: false },
)

watch(
	() => props.selectedEvent,
	(newVal, oldVal) => {
		// When the selected event changes, ensure the year is in view
		// In timeline mode, this happens instantly, at the same time as the line transition,
		// so that we don't see any movement, but we are in the right place to transition back to default mode,
		console.log(
			'selected event changed, scrolling to',
			selectedYear.value,
			rowsToShow.value,
		)
		if (newVal !== oldVal && container.value) {
			const yearsOffset = selectedYear.value - startYear.value
			const scrollOffset = 0.5 * (yearsOffset * 2)
			container.value.scrollTo({
				top: scrollOffset * rowHeight.value,
				behavior: props.mode === 'timeline' ? 'auto' : 'smooth',
			})
		}
	},
)

watch(
	() => [props.start, props.end],
	() => {
		if (model.value > props.end) {
			model.value = new Date(props.end.getTime())
		} else if (model.value < props.start) {
			model.value = new Date(props.start.getTime())
		}
	},
)

const xScaleFactor = ref(3)
const viewportTransform = computed(() => {
	if (props.selectedEvent && props.mode === 'eventzoom') {
		const eventStart = getDayOfYear(props.selectedEvent.times[0])
		const eventEnd = getDayOfYear(
			props.selectedEvent.times[props.selectedEvent.times.length - 1],
		)
		// TODO Get the event window and check its size relative to the time reel panel
		// Then scale and offset accordingly
		const nDays = (eventEnd - eventStart) * xScaleFactor.value
		const scale = Math.max(1, 366 / nDays)

		// return 'translate(0, 0)'
		return `scale(${scale}, 1) translate(${-(eventStart - 1)}, 0)`
	} else {
		return 'translate(0, 0)'
	}
})

const lineTransform = computed(() => {
	return (year: number): string =>
		props.mode === 'timeline'
			? `translate(0,${selectedYear.value - year}) scale(${1.0 / years.value.length}, 1)`
			: props.mode === 'overview'
				? `translate(${0.5 - differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)},0) scale(1, 1.25)`
				: `translate(${0.5 - differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)},0)`
})

const yearTransform = computed(() => {
	return (year: number): string =>
		`translate(0, ${year - startYear.value + 0.5})`
})

const lineOpacity = computed(() => {
	return (year: number): number => {
		return props.showBars &&
			props.mode !== 'timeline' &&
			selectedYear.value === year
			? 0.5
			: 1
	}
})

const yearPadding = computed(() => {
	if (props.mode === 'overview') return 0
	return (rowsToShow.value - 1) * 0.5 * rowHeight.value
})
</script>

<template>
	<div class="time-reel" ref="timeReelRef">
		<div
			class="date-info"
			:class="{ dragging: isDragging }"
			:style="`left: ${isDragging ? needleOffset : 50}%; top: ${isDragging ? '25%' : '-10%'};`"
		>
			{{ dayStr(selectedDay, selectedYear, props.mode === 'timeline') }}
		</div>
		<div
			class="controls"
			:class="{
				hidden: !(props.mode === 'default' || props.mode === 'eventzoom'),
				zoom: props.mode === 'eventzoom',
			}"
		>
			<div class="buttons">
				<button
					@click="prevYear"
					:disabled="selectedYear <= startYear"
					:title="$l.prevYear"
				>
					<span class="sr-only">{{ $l.prevYear }}</span>
					<font-awesome-icon
						:icon="faBackwardStep"
						style="transform: rotate(90deg)"
					/>
				</button>
				<button @click="startOfYear" :title="$l.startOfYear">
					<span class="sr-only">{{ $l.startOfYear }}</span>
					<font-awesome-icon :icon="faFastBackward" />
				</button>
				<button
					@click.stop="prevDay"
					:disabled="selectedYear <= startYear && selectedDay <= 1"
					:title="$l.prevDay"
				>
					<span class="sr-only">{{ $l.prevDay }}</span>
					<font-awesome-icon :icon="faBackwardStep" />
				</button>
				<button @click="togglePlay" :title="$l.play">
					<span class="sr-only">{{ $l.play }}</span>
					<font-awesome-icon :icon="playing ? faPause : faPlay" />
				</button>
				<button
					@click="nextDay"
					:disabled="selectedYear >= endYear && selectedDay >= 365"
					:title="$l.nextDay"
				>
					<span class="sr-only">{{ $l.nextDay }}</span>
					<font-awesome-icon :icon="faForwardStep" />
				</button>
				<button @click="endOfYear" :title="$l.endOfYear">
					<span class="sr-only">{{ $l.endOfYear }}</span>
					<font-awesome-icon :icon="faFastForward" />
				</button>
				<button
					@click="nextYear"
					:disabled="selectedYear >= endYear"
					:title="$l.nextYear"
				>
					<span class="sr-only">{{ $l.nextYear }}</span>
					<font-awesome-icon
						:icon="faForwardStep"
						style="transform: rotate(90deg)"
					/>
				</button>
			</div>
		</div>
		<div
			class="scroller"
			@scroll="scrollListener"
			@mousedown="startDrag"
			@prevent.default
			:class="{
				timeline: props.mode === 'timeline',
				overview: props.mode === 'overview',
				eventzoom: props.mode === 'eventzoom',
			}"
		>
			<div class="scrollee" :style="`margin: ${yearPadding}px 0;`">
				<div
					v-for="year in years"
					:key="year"
					:style="`height: ${rowHeight}px;`"
					class="year"
					:class="{
						timeline: mode === 'timeline',
						highlight: year === selectedYear,
						odd: year % 2 === 1,
						'last-year': year === endYear,
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
						preserveAspectRatio="none"
					>
						<defs>
							<linearGradient id="heatColdGradient" x1="0" y1="0" x2="0" y2="1">
								<stop offset="0%" :stop-color="scssVars.c3sred" />
								<stop offset="49%" :stop-color="scssVars.c3sred" />
								<stop offset="51%" :stop-color="scssVars.c3sblue" />
								<stop offset="100%" :stop-color="scssVars.c3sblue" />
							</linearGradient>
						</defs>
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
									:class="{ hot: props.hot, cold: props.cold }"
									d=""
									vector-effect="non-scaling-stroke"
									:stroke-width="3"
									:transform="lineTransform(year)"
									:opacity="lineOpacity(year)"
								/>
								<transition-group
									tag="g"
									name="daily-event-fx"
									v-if="
										(showBars && props.mode !== 'overview') ||
										props.mode === 'eventzoom'
									"
								>
									<rect
										v-if="year === selectedYear"
										v-for="box in eventBoxesForYear[year]"
										class="event-bar"
										:data-id="`${box.startX}-${box.endX}`"
										:class="{
											[box.event.event_type]: true,
											selected: box.event.id === props.selectedEvent?.id,
										}"
										:fill="colorForEvent(box.event) || scssVars.c3sred"
										:x="-0.5 + box.startX - year * TOTAL_DAYS"
										:width="box.endX - box.startX + 1"
										:y="positionY(box.y, box.event.event_type)"
										:height="
											props.hot && props.cold ? 0.5 * eventHeight : eventHeight
										"
										:key="box.event.id"
										vector-effect="non-scaling-stroke"
										@click="$emit('eventSelected', box.event.id)"
									></rect>
								</transition-group>
								<rect
									v-for="(month, i) in monthsForYear(
										year,
										props.mode === 'default' || props.mode === 'overview',
										$l,
									)"
									:key="`year-bg-${year}-month-${i}`"
									class="background month-bg"
									:class="{ oddyear: year % 2 === 0 }"
									:x="month.startX"
									:width="month.length"
									:y="-0.5"
									:height="1"
									:fill="month.color"
									:opacity="zoom || props.mode === 'timeline' ? 0 : 1"
								/>
								<rect
									v-for="year in years"
									:key="`year-bg-${year}`"
									class="background year-bg"
									:class="{ oddyear: year % 2 === 0 }"
									:x="(year - startYear) * (366 / years.length)"
									:width="366 / years.length"
									:y="-0.5"
									:height="1"
									:fill="
										year % 2 === 0
											? 'rgba(200,200,200,0.1)'
											: 'rgba(100,100,100,0.1)'
									"
									:opacity="props.mode === 'timeline' ? 1 : 0"
								/>
							</g>
						</g>
					</svg>
				</div>
			</div>
		</div>

		<div
			class="year-highlights"
			@prevent.default
			:class="{
				timeline: props.mode === 'timeline',
				overview: props.mode === 'overview',
				eventzoom: props.mode === 'eventzoom',
			}"
		>
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
					v-if="
						props.mode === 'default' ||
						props.mode === 'eventzoom' ||
						selectedEvent
					"
					:style="`left: ${needleOffset}%; pointer-events: none;`"
				>
					<div class="line" />
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

	.date-info {
		position: absolute;
		top: -10%;
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		background-color: rgba(255, 255, 255, 0.8);
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		user-select: none;
		transition: all $animTime linear;

		&.dragging {
			transition: left 0s linear;
			transition: top $animTime linear;
			transform: translateX(-50%) translateY(-100%);
		}
	}

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
					transition: all $animTime linear;
					top: 0;
					left: 0;
					height: 100%;
					background-color: transparent;
					width: 100%;
					margin: 0;
					padding: 0;
					overflow: visible;
					.background {
						transition: all $animTime linear;
						&.oddyear {
							background-color: rgba($c3sblue, 0.1);
						}
					}
				}
			}

			.year {
				// border: 2px solid red;
				transition:
					all $animTime linear,
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
					user-select: none;
				}
			}
		}
		&.overview {
			.event-line {
				stroke-width: 2;
				opacity: 0.8;
			}
			.scrollee {
				// padding-bottom: 1.5rem;
				.year {
					h1.label {
						font-size: 0.75rem !important;
						padding: 0 !important;
					}

					&.last-year {
						// padding-bottom: 1.5rem;
					}
				}
				.clipper {
					.events-svg {
						margin-right: 2.5rem;
						// margin-bottom: 1.5rem;
						width: calc(100% - 2.5rem);
						height: calc(100%);
					}
				}
			}
		}
	}

	.event-line {
		stroke: $c3sblue;
		stroke-width: 3;
		fill: $c3sblue;
		fill-opacity: 0.25;
		pointer-events: none;
		// transition: all $animTime linear;

		&.hot {
			stroke: $c3sred;
			fill: $c3sred;
		}
		&.cold {
			stroke: $c3sblue;
			fill: $c3sblue;
		}
		&.hot.cold {
			stroke: url(#heatColdGradient);
			fill: url(#heatColdGradient);
		}
	}

	.timeline {
		.event-line {
			stroke-width: 0.5;
			transition: all 0 linear;
		}
		.highlight-row {
			transition: all $animTime linear;
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
		transition: all $animTime linear;
		border: none;

		$fadeColor: #aaaaaa;

		&.overview {
			.month-labels {
				padding-right: 2.5rem;
				// width: calc(100% - 2.5rem);
			}
		}

		.highlight-row {
			transition: all $animTime linear;
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
						transition: opacity $animTime linear;

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
			transition: all $animTime linear;
		}

		.background {
			pointer-events: none;
			stroke: 0;
		}

		.event-bar {
			// This
			pointer-events: none;
			transition: all 0.25 * $animTime linear;
			stroke-width: 0.5;

			&.hot {
				stroke: $c3sred;
			}
			&.cold {
				stroke: $c3sblue;
			}
			&.selected {
				stroke: $lightbulb;
				// stroke-width: 2;
				pointer-events: auto;
				cursor: pointer;
				fill: $lightbulb;
				filter: drop-shadow(0 0 2px $lightbulb) drop-shadow(0 0 4px $lightbulb);
				// transform: scaleY(1);
			}
		}
		.day-box {
			stroke-width: 2;
			opacity: 1;
		}

		.daily-event-fx-enter-from {
			opacity: 0;
			transition: opacity $animTime linear;
		}
		.daily-event-fx-enter-to {
			opacity: 1;
		}

		.daily-event-fx-leave-from {
			opacity: 1;
			transition: opacity $animTime linear;
		}
		.daily-event-fx-leave-to {
			opacity: 0;
		}

		// .selected-event-fx-enter-from {
		// 	opacity: 0;
		// 	stroke-width: 0;
		// }
		// .selected-event-fx-enter-to {
		// 	opacity: 1;
		// 	stroke-width: 2;
		// }
		// .selected-event-fx-enter-active {
		// 	// transition:
		// 	// 	stroke-width 0s ease-out calc($animTime + $settleTime + var(--i) * 20ms),
		// 	// 	opacity 0s ease-out calc($animTime + $settleTime);
		// }

		// .selected-event-fx-leave-from {
		// 	opacity: 1;
		// 	stroke-width: 2;
		// }
		// .selected-event-fx-leave-to {
		// 	opacity: 0;
		// 	stroke-width: 0;
		// }
		// .selected-event-fx-leave-active {
		// 	// transition:
		// 	// 	stroke-width $animTime ease calc(var(--i) * 20ms) $settleTime,
		// 	// 	opacity $animTime linear $settleTime;
		// 	// transition:
		// 	// 	transform 0s linear,
		// 	// 	stroke-width 0s ease-out calc(var(--i) * 20ms),
		// 	// 	opacity 0s ease-out $settleTime;
		// }
	}
}
</style>
