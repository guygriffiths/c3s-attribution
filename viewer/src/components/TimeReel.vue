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
	nextTick,
} from 'vue'
import { catScheme } from '@/store/store'
import { useLabels } from '@/lib/labels'

interface WeatherEvent {
	id: number
	startDate: Date
	endDate: Date
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
	selectedEvent: { type: Object as () => WeatherEvent | null, default: null },
	zoom: { type: Boolean, default: false },
})

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})

const needleRef = ref<HTMLDivElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// const yearHeight = ref(96)
const rowsToShow = computed(() => props.zoom ? 1 : 3)

const totalDays = 366

const selectedDay = computed(() => getDayOfYear(model.value))
const selectedYear = computed(() => model.value.getUTCFullYear())

const startYear = computed(() => props.start.getUTCFullYear())
const endYear = computed(() => props.end.getUTCFullYear())
const totalYears = computed(() => endYear.value - startYear.value + 1)
const years = computed(() =>
	Array.from({ length: totalYears.value }, (_, i) => startYear.value + i),
)
const eventsByYear = ref<Map<number, WeatherEvent[]>>(new Map())
const maxSimultaneousEvents = ref(0)

const dayStr = (day: number) => {
	day = Math.max(1, Math.min(day, totalDays))
	const date = setDayOfYear(new Date(selectedYear.value, 0, 1), day)
	return format(date, 'do MMMM')
}

const populateEvents = () => {
	years.value.forEach((year) => {
		const { events: eventsForYear, maxEvents } = assignTimelinePositions(
			props.events,
			year,
		)

		maxSimultaneousEvents.value = Math.max(
			maxSimultaneousEvents.value,
			maxEvents,
		)
		eventsByYear.value.set(year, eventsForYear)
	})
	console.log('Cached events:', eventsByYear.value)
}

const eventIsSelected = (event: { id?: number }) =>
	event.id === props.selectedEvent?.id
const eventHeight = computed(() => 0.02)//0.75 / maxSimultaneousEvents.value)
const isYearVisible = (year: number) => Math.abs(selectedYear.value - year) <= 2

watch(() => props.events, populateEvents, { immediate: true, deep: true })

const isDragging = ref(false)
const dragMode = ref<'horizontal' | 'vertical' | null>(null)
let startX = 0
let startY = 0
const yOffset = computed(() => {
	const scrollPos = (model.value.getUTCFullYear() - startYear.value + 1)
	return scrollPos - Math.floor(rowsToShow.value / 2)
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

	selectedDay.value = Math.round(selectedDay.value)
	selectedDay.value = Math.max(1, Math.min(selectedDay.value, totalDays))

	const tempDate = setDayOfYear(
		new Date(Date.UTC(selectedYear.value, 0, 1)),
		selectedDay.value,
	)
	model.value = new Date(
		Date.UTC(tempDate.getFullYear(), tempDate.getMonth(), tempDate.getDate()),
	)
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
			// selectedDay.value = Math.max(0, Math.min(1, percentage)) * totalDays

			const tempDate = setDayOfYear(
				new Date(Date.UTC(selectedYear.value, 0, 1)),
				Math.max(0, Math.min(1, percentage)) * totalDays,
			)
			model.value = new Date(
				Date.UTC(
					tempDate.getFullYear(),
					tempDate.getMonth(),
					tempDate.getDate(),
				),
			)
		}
	} else if (dragMode.value === 'vertical') {
		// yOffset.value -= dy
		// yOffset.value = Math.max(0, yOffset.value)
		if (dy > 0) {
			model.value = subYears(model.value, 1)
		} else {
			model.value = addYears(model.value, 1)
		}
		startY = event.clientY
	}
}

const onWheel = (e: WheelEvent) => {
	e.preventDefault()
	if (e.shiftKey || e.metaKey) {
		// const delta = e.deltaY > 0 ? 1.1 : 0.9
		// scaleX.value = Math.max(0.1, Math.min(scaleX.value * delta, 20))
		if (e.deltaY < 0) {
			model.value = subHours(model.value, 24)
		} else {
			model.value = addHours(model.value, 24)
		}
	} else {
		if (e.deltaY < 0) {
			model.value = subYears(model.value, 1)
		} else {
			model.value = addYears(model.value, 1)
		}
	}
}

const viewportTransform = computed(() => {
	const yScale = totalYears.value / rowsToShow.value

	if (!props.selectedEvent) {
		return `translate(0, ${yScale*(1-yOffset.value)}) scale(1, ${yScale})`
	} else {
		const eventStart = getDayOfYear(props.selectedEvent.startDate)
		const eventEnd = getDayOfYear(props.selectedEvent.endDate)
		const totalDays = eventEnd - eventStart + 2
		const scale = 366 / totalDays
		return `translate(${scale*(1-eventStart)}, ${yScale*(1-yOffset.value)}) scale(${scale}, ${yScale})`
	}
})

function assignTimelinePositions(events: WeatherEvent[], targetYear: number) {
	const filtered = events.filter(
		(e) =>
			e.times[0].getFullYear() <= targetYear &&
			e.times[e.times.length - 1].getFullYear() >= targetYear,
	)

	const sliced = filtered.map((e) => {
		const startDay =
			e.times[0].getFullYear() < targetYear ? 1 : getDayOfYear(e.times[0])
		const endDay =
			e.times[e.times.length - 1].getFullYear() > targetYear
				? (new Date(targetYear, 11, 31).getTime() -
						new Date(targetYear, 0, 0).getTime()) /
					86400000
				: getDayOfYear(e.times[e.times.length - 1])
		return { ...e, startX: startDay, endX: endDay }
	})

	let maxy = 0
	const activeRows: any[] = []
	const result = sliced
		.sort((a, b) => a.startX - b.startX)
		.map((event) => {
			const usedYs = new Set()
			for (const row of activeRows) {
				if (row.endX >= event.startX) usedYs.add(row.y)
			}
			let y = 0
			while (usedYs.has(y)) y++
			activeRows.push({ endX: event.endX, y })
			event.y = y
			maxy = Math.max(maxy, y)
			event.color = catScheme[event.id % catScheme.length]
			return event
		})

	return { events: result, maxEvents: maxy }
}

const needleOffset = computed(() => {
	if (!props.zoom) {
		const offset = (selectedDay.value / totalDays) * 100
		return Math.max(Math.min(offset, 100), 0)
	} else {
		// In zoom mode, we want to center the needle on the selected event
		if (props.selectedEvent) {
			const eventStart = getDayOfYear(props.selectedEvent.startDate)
			const eventEnd = getDayOfYear(props.selectedEvent.endDate)
			const totalDays = eventEnd - eventStart + 4
			const midDay = (eventStart + eventEnd) / 2
			return ((midDay / totalDays) * 100).toFixed(2)
		} else {
			return ((selectedDay.value / totalDays) * 100).toFixed(2)
		}
	}
})

const positionY = (y: number) => {
	if (y % 2 === 0) {
		return -0.55 * eventHeight.value * y
	} else {
		return 0.55 * eventHeight.value * (y + 1)
	}
}

onMounted(() => {
	const handleKey = (e: KeyboardEvent) => {
		if (e.key === 'PageUp') model.value = subHours(model.value, 24)
		else if (e.key === 'PageDown') model.value = addHours(model.value, 24)
		else if (e.key === 'ArrowLeft') model.value = subHours(model.value, 24)
		else if (e.key === 'ArrowRight') model.value = addHours(model.value, 24)
		else if (e.key === 'ArrowUp') model.value = subYears(model.value, 1)
		else if (e.key === 'ArrowDown') model.value = addYears(model.value, 1)
	}
	window.addEventListener('keydown', handleKey)
	populateEvents()

	onBeforeUnmount(() => {
		window.removeEventListener('keydown', handleKey)
	})
})
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
					v-show="() => true || isYearVisible(year)"
					:transform="`translate(0, ${0.5 + year - startYear})`"
				>
					<rect
						v-for="event in eventsByYear.get(year)"
						:x="event.startX! - 0.5"
						:width="event.endX! - event.startX! + 1"
						:y="eventIsSelected(event) ? -0.5 : positionY(event.y!)"
						:height="eventIsSelected(event) ? 3 * eventHeight : eventHeight"
						:fill="event.color"
					/>
				</g>
			</g>
		</svg>

		<div class="year-highlights">
			<div
				class="highlight-row fade-top"
				:class="{ zoom: props.zoom }"
				:style="`flex: 0 0 calc( 0.5 * ( 100% - ( 100% / ${rowsToShow} ) )`"
			></div>
			<div
				class="highlight-row highlight"
				:style="`flex: 0 0 calc(100% / ${rowsToShow});`"
			>
				<div
					class="needle"
					ref="needleRef"
					:style="`left: ${needleOffset}%;`"
					@mousedown="startDrag"
				>
					<div class="line" />
					<div class="label" :class="{ hidden: !isDragging }">
						<p>{{ dayStr(selectedDay) }}</p>
					</div>
				</div>
				<p v-show="!props.zoom" class="jan">{{ $l.months.jan }}</p>
				<p v-show="!props.zoom" class="feb">{{ $l.months.feb }}</p>
				<p v-show="!props.zoom" class="mar">{{ $l.months.mar }}</p>
				<p v-show="!props.zoom" class="apr">{{ $l.months.apr }}</p>
				<p v-show="!props.zoom" class="may">{{ $l.months.may }}</p>
				<p v-show="!props.zoom" class="jun">{{ $l.months.jun }}</p>
				<p v-show="!props.zoom" class="jul">{{ $l.months.jul }}</p>
				<p v-show="!props.zoom" class="aug">{{ $l.months.aug }}</p>
				<p v-show="!props.zoom" class="sep">{{ $l.months.sep }}</p>
				<p v-show="!props.zoom" class="oct">{{ $l.months.oct }}</p>
				<p v-show="!props.zoom" class="nov">{{ $l.months.nov }}</p>
				<p v-show="!props.zoom" class="dec">{{ $l.months.dec }}</p>
			</div>
			<div
				class="highlight-row fade-bottom"
				:style="`flex: 0 0 calc( 0.5 * ( 100% - ( 100% / ${rowsToShow} ) )`"
			></div>
		</div>
		<!-- <div class="debug">
			<button @click="testFocusY">testFocusY</button>
			<button @click="testFocusX">testFocusX</button>
			<button @click="resetFocus">Reset Zoom</button>
		</div> -->
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

$margin: 0 0.5rem;
$margin: 0 0;
.time-reel {
	position: relative;
}

.event-background {
	position: absolute;
	top: 0;
	left: 0;
	height: 100%;
	width: 100%;
	margin: $margin;
	border: 1px solid #ccc;
	position: relative;
	padding: 0;

	.scroller {
		transition: transform $animTime ease-in-out;
	}

	rect {
		transition: all $settleTime ease-in-out calc(0.5*$animTime);
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
		&.fade-top {
			pointer-events: none;
			background: linear-gradient(
				to top,
				rgba($fadeColor, 0.3),
				rgba($fadeColor, 1)
			);
		}
		&.fade-bottom {
			pointer-events: none;
			background: linear-gradient(
				to bottom,
				rgba($fadeColor, 0.3),
				rgba($fadeColor, 1)
			);
		}
		&.highlight {
			position: relative;
			width: 100%;
			border: 1px solid #aaaaaa;
			display: flex;
			flex-direction: row;
			align-items: stretch;
			color: #aaaaaa;
			box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
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
