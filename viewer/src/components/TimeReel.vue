<script setup lang="ts">
import {
	format,
	getDayOfYear,
	setDayOfYear,
	addHours,
	subHours,
	addYears,
	subYears,
} from 'date-fns'
import {
	ref,
	computed,
	defineModel,
	Ref,
	watch,
	onMounted,
	onBeforeUnmount,
} from 'vue'
import { useLabels } from '@/lib/labels'
import * as d3 from 'd3'
import scssVars from '@/assets/styles/scssVars.module.scss'
import { monthsForYear, TOTAL_DAYS, dayStr } from '@/lib/time-utils'

interface WeatherEvent {
	id: string
	times: Date[]
	color?: string
	y?: number
	startX?: number
	endX?: number
}

const $l = useLabels()

const props = defineProps({
	start: { type: Date, default: () => new Date(1970, 0, 1) },
	end: { type: Date, default: () => new Date(2024, 0, 1) },
	events: { type: Array<WeatherEvent>, default: () => [] as WeatherEvent[] },
	dayCounts: { type: Map<number, Array<number>>, default: () => new Map() },
	selectedEvent: { type: Object as () => WeatherEvent | null, default: null },
	changingFilter: { type: Boolean, default: false },
	exploring: { type: Boolean, default: false },
	vertical: { type: Boolean, default: false },
	showBars: { type: Boolean, default: true },
})

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})
const emits = defineEmits<{
	(event: 'eventSelected', id: string): void
}>()
const nextDay = () => {
	const newVal = addHours(model.value, 24)
	if (newVal.getUTCFullYear() <= props.end.getUTCFullYear()) {
		model.value = newVal
	}
}
const prevDay = () => {
	const newVal = subHours(model.value, 24)
	if (newVal.getUTCFullYear() >= props.start.getUTCFullYear()) {
		model.value = newVal
	}
}
const nextYear = () => {
	const newVal = addYears(model.value, 1)
	if (newVal.getUTCFullYear() <= props.end.getUTCFullYear()) {
		model.value = newVal
	}
}
const prevYear = () => {
	const newVal = subYears(model.value, 1)
	if (newVal.getUTCFullYear() >= props.start.getUTCFullYear()) {
		model.value = newVal
	}
}
const setDate = (date: Date) => {
	if (
		date.getUTCFullYear() >= props.start.getUTCFullYear() &&
		date.getUTCFullYear() <= props.end.getUTCFullYear()
	) {
		model.value = date
	}
}

const needleRef = ref<HTMLDivElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

const zoom = computed(() => props.selectedEvent !== null)
const rowsToShow = computed(() => {
	if (zoom.value) return 1
	if (props.exploring) {
		return Math.min(50, endYear.value - startYear.value + 1)
	}
	if (props.vertical) {
		return Math.min(50, endYear.value - startYear.value + 1)
	}
	return 2
})

const selectedDay = computed(() => getDayOfYear(model.value))
const selectedYear = computed(() => model.value.getUTCFullYear())

const startYear = computed(() => props.start.getUTCFullYear())
const endYear = computed(() => props.end.getUTCFullYear())
const totalYears = computed(() => endYear.value - startYear.value + 1)
const years = computed(() =>
	Array.from(
		{ length: totalYears.value + rowsToShow.value },
		(_, i) => startYear.value + i - Math.floor(rowsToShow.value / 2),
	),
)
const eventsByYear = ref<Map<number, WeatherEvent[]>>(new Map())
const maxSimultaneousEvents = computed(() => {
	// Find max of props.dayCounts here
	if (props.dayCounts.size < 1) return 3
	return Math.max(3, 
		...Array.from(props.dayCounts.values()).map((counts) =>
			Math.max(...counts),
		),
	)
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
const eventHeight = computed(
	() => (props.selectedEvent !== null ? 1 : 0.8) / maxSimultaneousEvents.value,
)

import { debounce } from '@/lib/utils'

watch(
	() => props.events,
	() => {
		// debounce(() => populateEvents(), 25)
		populateEvents()
	},
	{ immediate: true, deep: false },
)

const isDragging = ref(false)
const dragMode = ref<'horizontal' | 'vertical' | null>(null)
let startX = 0
let startY = 0
const yOffset = computed(() => {
	// with 4 rows: 1981: -0.5, 1982: 0.5, 1983: 1.5, 1984: 2.5
	// with 3 rows: 1981: 0, 1982: 1, 1983: 2
	// with 2 rows: 1981: 0.5, 1982: 1.5, 1983: 2.5
	// with 1 row: 1981: 1, 1982: 2, 1983: 3
	// with "0" rows: 1981: 1.5, 1982: 2.5, 1983: 3.5

	const offset =
		model.value.getUTCFullYear() - startYear.value + 1.5 - rowsToShow.value / 2
	if (props.exploring) {
		return Math.min(1, offset)
	}
	if (props.vertical) {
		// return Math.min(1, offset)
		return 1 - 0.25
	}

	return offset
})

const startDrag = (event: MouseEvent) => {
	isDragging.value = true
	dragMode.value = null
	startX = event.clientX
	startY = event.clientY
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', endDrag)
}

const endDrag = () => {
	isDragging.value = false
	dragMode.value = null
	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', endDrag)

	// selectedDay.value = Math.round(selectedDay.value)
	// selectedDay.value = Math.max(1, Math.min(selectedDay.value, totalDays))
	//
	// const tempDate = setDayOfYear(
	// 	new Date(Date.UTC(selectedYear.value, 0, 1)),
	// 	selectedDay.value,
	// )
	// setDate(
	// 	new Date(Date.UTC(tempDate.getFullYear(), tempDate.getMonth(), tempDate.getDate())),
	// )
	console.log(`Just set model to ${model.value.toISOString()}`)
}

const handleDrag = (event: MouseEvent) => {
	console.warn('Dragging does not properly work yet')
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
			const offsetX = event.clientX - rect.left
			const percentage = offsetX / rect.width
			const totalDays = selectedYear.value % 4 === 0 ? 365 : 364

			if (!props.selectedEvent) {
				const dayOfYear = Math.floor(
					1 + Math.max(0, Math.min(1, percentage)) * totalDays,
				)
				const tempDate = setDayOfYear(
					new Date(Date.UTC(selectedYear.value, 0, 1)),
					dayOfYear,
				)

				setDate(
					new Date(
						Date.UTC(
							tempDate.getFullYear(),
							tempDate.getMonth(),
							tempDate.getDate(),
						),
					),
				)
			} else {
				const eventStart = getDayOfYear(props.selectedEvent.times[0])
				const eventEnd = getDayOfYear(
					props.selectedEvent.times[props.selectedEvent.times.length - 1],
				)
				const dragDays = eventEnd - eventStart + 2

				const dayFromStart = Math.floor(
					1 + Math.max(0, Math.min(1, percentage)) * dragDays,
				)
				const tempDate = setDayOfYear(
					new Date(Date.UTC(selectedYear.value, 0, 1)),
					dayFromStart + eventStart - 1,
				)

				setDate(
					new Date(
						Date.UTC(
							tempDate.getFullYear(),
							tempDate.getMonth(),
							tempDate.getDate(),
						),
					),
				)
			}
		}
	} else if (dragMode.value === 'vertical') {
		// yOffset.value -= dy
		// yOffset.value = Math.max(0, yOffset.value)
		if (dy > 0) {
			prevYear()
		} else {
			nextYear()
		}
		startY = event.clientY
	}
}

const TRACK_THRESHOLD = 10 // pixels
const onWheel = (e: WheelEvent) => {
	if (e.shiftKey || e.metaKey) {
		if (e.deltaY < 0) {
			prevDay()
		} else {
			nextDay()
		}
	} else {
		console.log('wheel scrolling is kinda shit with a trackpad :(')
		if (e.deltaY < 0) {
			prevYear()
		} else if (e.deltaY > 0) {
			nextYear()
		}
	}
}

const eventClicked = (event: WeatherEvent) => {
	emits('eventSelected', event.id)
}

const viewportTransform = computed(() => {
	const yScale = totalYears.value / rowsToShow.value

	if (!props.selectedEvent) {
		return `translate(0, ${yScale * (1 - yOffset.value)}) scale(1, ${yScale})`
	} else {
		const eventStart = getDayOfYear(props.selectedEvent.times[0])
		const eventEnd = getDayOfYear(
			props.selectedEvent.times[props.selectedEvent.times.length - 1],
		)
		const nDays = eventEnd - eventStart + 2
		const scale = 366 / nDays

		return `translate(${scale * (1 - eventStart)}, ${yScale * (1 - yOffset.value)}) scale(${scale}, ${yScale})`
	}
})

function assignTimelinePositions(events: WeatherEvent[], targetYear: number) {
	const yearStart = new Date(targetYear, 0, 0).getTime()
	const yearEnd = new Date(targetYear + 1, 0, 0).getTime() - 1

	// Step 1: Filter and slice in one go, reuse timestamps to avoid creating Date objects
	const sliced: (WeatherEvent & { startX: number; endX: number })[] = []
	for (let i = 0; i < events.length; i++) {
		const e = events[i]
		const first = e.times[0]
		const last = e.times[e.times.length - 1]

		if (last.getTime() < yearStart || first.getTime() > yearEnd) continue

		const startX = first.getTime() < yearStart ? 1 : getDayOfYear(first)
		const endX =
			last.getTime() > yearEnd
				? (yearEnd - yearStart) / 86400000
				: getDayOfYear(last)

		sliced.push({ ...e, startX, endX })
	}

	// Step 2: Assign y-positions using a greedy row-packing algorithm
	const rows: number[] = [] // row[y] = lastEndX
	const result = new Array(sliced.length)

	sliced.sort((a, b) => a.startX - b.startX)

	let maxY = 0
	for (let i = 0; i < sliced.length; i++) {
		const e = sliced[i]
		let y = 0
		for (; y < rows.length; y++) {
			if (rows[y] < e.startX) break
		}
		e.y = y
		rows[y] = e.endX
		if (y > maxY) maxY = y
		result[i] = e
	}

	return { events: result, maxEvents: maxY }
}

const needleOffset = computed(() => {
	if (!zoom.value) {
		const offset = (selectedDay.value / TOTAL_DAYS) * 100
		return Math.max(Math.min(offset, 100), 0)
	} else {
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
		} else {
			return ((selectedDay.value / TOTAL_DAYS) * 100).toFixed(2)
		}
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
	const handleKey = (e: KeyboardEvent) => {
		// TODO Should all of this go in a global key handler? Perhaps not, since people use arrow keys on maps?
		if(props.vertical) return
		if (e.key === 'PageUp') prevDay()
		else if (e.key === 'PageDown') nextDay()
		else if (e.key === 'ArrowLeft') prevDay()
		else if (e.key === 'ArrowRight') nextDay()
		else if (e.key === 'ArrowUp') prevYear()
		else if (e.key === 'ArrowDown') nextYear()
		else if (e.key === 'Home') setDate(new Date(props.start.getTime()))
		else if (e.key === 'End') setDate(new Date(props.end.getTime()))
		else if (e.key === 'Escape') {
			if (isDragging.value) endDrag()
		}
	}
	window.addEventListener('keydown', handleKey)
	populateEvents()

	onBeforeUnmount(() => {
		window.removeEventListener('keydown', handleKey)
	})
})

const topBottomRowFlex = computed(
	() => `0 0 calc(0.5 * (100% - (100% / ${rowsToShow.value})))`,
)
const highlightRowFlex = computed(() => `0 0 calc(100% / ${rowsToShow.value})`)

const getAreaForYear = (year: number) => {
	if (!props.dayCounts.has(year)) return ''
	const data: Array<{ x: number; y: number }> = props.dayCounts
		.get(year)!
		.map((d, i) => ({
			x: i,
			y: d,
		}))
	const xScale = d3.scaleLinear().domain([0, 366]).range([1.5, 367.5])
	const yScale = d3
		.scaleLinear()
		.domain([0, 1.05 * maxSimultaneousEvents.value])
		.range([0, 0.5])
	const areaStr = d3
		.area<{ x: number; y: number }>()
		.x((d) => xScale(d.x))
		.y0((d) => -yScale(d.y))
		.y1((d) => yScale(d.y))
		.defined((d) => d.x >= 0 && d.x < 366)
		.curve(d3.curveMonotoneX)(data! || [])
	if (year === 2024) {
		// console.log(`Line for year ${year}: ${areaStr}`)
	}
	return areaStr || ''
}

const yearLines: Record<number, string> = {}
watch(
	() => [props.dayCounts, props.vertical],
	() => {
		for (const year of years.value) {
			const newD = getAreaForYear(year)
			const animTime = parseFloat(scssVars.animTime.replaceAll('s', '')) * 1000
			d3.select(`#events-line-${year}`)
				.transition()
				.duration(animTime)
				.attr('d', newD)
				.on('end', () => {
					if (props.dayCounts.has(year)) {
						yearLines[year] = newD
					} else {
						yearLines[year] = ''
					}
				})
		}
	},
	{ immediate: true, deep: true },
)
</script>

<template>
	<div class="time-reel">
		<svg
			class="event-background"
			ref="containerRef"
			xmlns="http://www.w3.org/2000/svg"
			:viewBox="`0 0 366 ${endYear - startYear + 1}`"
			preserveAspectRatio="none"
			@wheel.passive="onWheel"
			@mousedown="startDrag"
		>
			<g :transform="viewportTransform" class="scroller">
				<g
					v-for="year in years"
					:key="year"
					:transform="`translate(0, ${0.5 + year - startYear})`"
				>
					<rect
						v-for="(month, i) in monthsForYear(
							year,
							props.vertical || props.exploring,
							$l,
						)"
						:key="`${year}${i}`"
						class="background"
						:x="!props.vertical ? month.startX : -0.5"
						:width="!props.vertical ? month.length : 366"
						:y="!props.vertical ? -0.5 : -0.5 + month.startX / 366"
						:height="!props.vertical ? 1 : month.length / 366"
						:fill="month.color"
						:opacity="zoom ? 0 : 1"
					/>
					<path
						:key="`${year}-line`"
						class="event-line"
						:id="`events-line-${year}`"
						:d="yearLines[year] || getAreaForYear(year)"
						vector-effect="non-scaling-stroke"
						:stroke-width="props.vertical ? 1 : 3"
						:opacity="
							props.showBars && !props.exploring && !props.vertical && year === selectedYear
								? 0.25
								: 1.0
						"
						:transform="
							props.vertical
								? `
							translate(${TOTAL_DAYS / 2},0)
							scale(${TOTAL_DAYS}, 1)  
							rotate(90)
							scale(${1 / TOTAL_DAYS}, 1)
							translate(${-TOTAL_DAYS / 2}, 0)
							`
								: ''
						"
					/>
					<transition-group tag="g" name="daily-event-fx" v-if="props.showBars">
						<rect
							v-for="event in eventsByYear
								.get(year)
								?.filter(() => !props.vertical && year == selectedYear) || []"
							class="event-bar"
							:data-id="event.id"
							:key="event.id"
							:x="
								!props.vertical
									? event.startX! - 0.5
									: TOTAL_DAYS * (0.5 + positionY(event.y!) - eventHeight)
							"
							:width="
								!props.vertical
									? event.endX! - event.startX! + 1
									: TOTAL_DAYS * eventHeight
							"
							:y="
								!props.vertical
									? eventIsSelected(event)
										? -0.5
										: positionY(event.y!) - 0.5 * eventHeight
									: -0.5 + (event.startX! - 0.5) / TOTAL_DAYS
							"
							:height="
								!props.vertical
									? eventIsSelected(event)
										? 3 * eventHeight
										: 0.9 * eventHeight
									: (event.endX! - event.startX! + 1) / TOTAL_DAYS
							"
							:fill="event.color"
							:class="{
								selected: eventIsSelected(event),
								unselected:
									!eventIsSelected(event) && props.selectedEvent !== null,
							}"
							:opacity="
								eventIsSelected(event) ||
								props.exploring ||
								year !== selectedYear
									? 0
									: 1
							"
							@click="eventClicked(event)"
						/>
					</transition-group>
				</g>
			</g>
			<transition-group
				tag="g"
				name="selected-event-fx"
				class="selected-event-fx"
				:transform="viewportTransform"
			>
				<rect
					v-for="(day, i) in props.selectedEvent?.times || []"
					:key="`${day.getTime()}-${props.selectedEvent?.id || ''}`"
					vector-effect="non-scaling-stroke"
					:x="getDayOfYear(day) - 0.5"
					:width="1"
					:y="(props.selectedEvent?.times[0].getFullYear() || 0) - startYear"
					:height="3 * eventHeight"
					stroke="white"
					:fill="props.selectedEvent?.color || '#ff0000'"
					class="day-box"
					:style="{ '--i': i }"
				/>
			</transition-group>
		</svg>

		<div class="year-highlights" v-if="!props.vertical && !props.exploring">
			<div
				class="highlight-row fade-top"
				:class="{ exploring: props.exploring }"
				:style="`flex: ${topBottomRowFlex};`"
			></div>
			<div
				class="highlight-row highlight"
				:style="`flex: ${highlightRowFlex};`"
				:class="{ exploring: props.exploring }"
			>
				<h2 class="year-label">
					{{ selectedYear }}
				</h2>
				<div
					class="needle"
					ref="needleRef"
					:style="`left: ${needleOffset}%;`"
					@mousedown="startDrag"
				>
					<div class="line" />
					<div class="label" :class="{ hidden: !isDragging }">
						<p>{{ dayStr(selectedDay, selectedYear) }}</p>
					</div>
				</div>
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
			<div
				class="highlight-row fade-bottom"
				:class="{ exploring: props.exploring }"
				:style="`flex: 0 0 calc( 0.5 * ( 100% - ( 100% / ${rowsToShow} ) )`"
			></div>
		</div>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

$margin: 0 0.5rem;
$margin: 0 0;
.time-reel {
	position: relative;
}

.event-line {
	stroke: $c3sblue;
	// stroke-width: 0.025;
	fill: $c3sblue;
	fill-opacity: 0.25;
	pointer-events: none;
	transition: opacity $animTime ease-in-out;
}

.heatmap {
	.event-line {
		stroke: $c3sred;
		fill: $c3sred;
	}
}

.event-background {
	position: absolute;
	top: 0;
	left: 0;
	height: 100%;
	width: 100%;
	margin: $margin;
	position: relative;
	padding: 0;

	.scroller {
		transition: transform $animTime ease-in-out;

		&.zoom {
			transition: transform $animTime ease-in-out $settleTime;
		}
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
				opacity 0s linear calc($animTime + $settleTime);
		}

		&.unselected {
			transition:
				all $settleTime ease-in-out,
				opacity 0 linear;
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
		// 	opacity $animTime linear $settleTime;
		transition:
			transform 0s ease-in-out,
			stroke-width 0s ease-out calc(var(--i) * 20ms),
			opacity 0s ease-out $settleTime;
	}
}

.year-highlights {
	padding: $margin;
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	z-index: 2;
	pointer-events: none;
	transition: all $animTime ease-in-out;
	border: none;

	$fadeColor: #aaaaaa;

	.highlight-row {
		transition: all $animTime ease-in-out;
		overflow: hidden;

		.year-label {
			position: absolute;
			text-align: center;
			margin: 0.5rem;
		}

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
				pointer-events: all;
				display: block;
				position: absolute;
				top: 0;
				left: 0;
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
					// left: 8px;
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
</style>
