<script setup lang="ts">
import {
	format,
	getDayOfYear,
	setDayOfYear,
	addHours,
	subHours,
	set,
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

const $l = useLabels()

const props = defineProps({
	start: {
		type: Date,
		default: () => new Date(1970, 0, 1),
	},
	end: {
		type: Date,
		default: () => new Date(2024, 0, 1),
	},
	events: {
		type: Array,
		default: () => [] as { startDate: Date; endDate: Date }[],
	},
	selectedEvent: {
		type: Object as () => { startDate: Date; endDate: Date } | null,
		default: null,
	},
	zoom: {
		type: Boolean,
		default: false,
	},
})

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})

const containerRef = ref<HTMLDivElement | null>(null)
const needleRef = ref<HTMLDivElement | null>(null)
const svgZoomWrapperRefs: Record<number, HTMLElement> = {}

const yearHeight = computed(() => {
	if (props.zoom) {
		return 96 // Height for zoomed-in view
	} else {
		return 96 // Height for normal view
	}
})
const rowsToShow = computed(() => {
	if (props.zoom) {
		return 1
	} else {
		return 3
	}
})
const totalDays = 366
const selectedDay = ref(getDayOfYear(model.value))
const selectedYear = ref(model.value.getUTCFullYear())

const startYear = computed(() => props.start.getUTCFullYear())
const endYear = computed(() => props.end.getUTCFullYear())
const totalYears = computed(() => endYear.value - startYear.value + 3)
const years = computed(() =>
	Array.from({ length: totalYears.value }, (_, i) => startYear.value - 1 + i),
)
const days = computed(() => Array.from({ length: totalDays }, (_, i) => i + 1))

const dayStr = (day: number) => {
	if (day < 1) day = 1
	if (day > totalDays) day = totalDays
	const date = setDayOfYear(new Date(selectedYear.value, 0, 1), day)
	return format(date, 'do MMMM')
}

const isEvenMonth = (day: number) => {
	const date = setDayOfYear(new Date(selectedYear.value, 0, 1), day)
	return date.getMonth() % 2 !== 0
}

const onScrollEnd = () => {
	// Snap to the nearest year and scroll to it
	console.log('Snapping to nearest year')
	if (containerRef.value) {
		const scrollTop = containerRef.value.scrollTop
		const yearIndex = Math.round(scrollTop / yearHeight.value)
		const targetScrollTop = yearIndex * yearHeight.value
		containerRef.value.scrollTo({ top: targetScrollTop, behavior: 'smooth' })

		const offset = Math.floor(rowsToShow.value / 2)
		selectedYear.value = years.value[yearIndex + offset]
		const newValue = setDayOfYear(
			new Date(Date.UTC(selectedYear.value, 0, 1, 0, 0, 0)),
			selectedDay.value,
		)
		model.value = new Date(
			Date.UTC(
				newValue.getFullYear(),
				newValue.getMonth(),
				newValue.getDate(),
				0,
				0,
				0,
			),
		)
	}
}

watch(
	() => [model.value, props.start, props.end],
	() => {
		nextTick(() => {
			selectedDay.value = getDayOfYear(model.value)
			selectedYear.value = model.value.getUTCFullYear()
			// Set the initial scroll position
			if (containerRef.value) {
				const yearIndex = years.value.findIndex(
					(year) => year === model.value.getUTCFullYear(),
				)
				const targetScrollTop =
					(yearIndex - Math.floor(rowsToShow.value / 2)) * yearHeight.value
				containerRef.value.scrollTo({ top: targetScrollTop, behavior: 'auto' })
			}
		})
	},
)

watch(
	() => props.selectedEvent,
	(newVal) => {
		console.log('Selected event changed:', newVal)
		if (newVal) {
			const event = newVal
			const startDay = getDayOfYear(event.startDate)
			const endDay = getDayOfYear(event.endDate)
			zoomToDays(startDay, endDay, selectedYear.value)
		} else {
			zoomToDays(1, totalDays, selectedYear.value)
		}
	},
)

onMounted(() => {
	const handleKey = (e: KeyboardEvent) => {
		if (e.key === 'PageUp') {
			model.value = subHours(model.value, 24)
		} else if (e.key === 'PageDown') {
			model.value = addHours(model.value, 24)
		}
	}

	window.addEventListener('keydown', handleKey)

	onBeforeUnmount(() => {
		window.removeEventListener('keydown', handleKey)
	})
})

const isDragging = ref(false)

const startDrag = (event: MouseEvent) => {
	isDragging.value = true
	window.addEventListener('mousemove', needleDrag)
	window.addEventListener('mouseup', endDrag)
}

const endDrag = () => {
	isDragging.value = false
	window.removeEventListener('mousemove', needleDrag)
	window.removeEventListener('mouseup', endDrag)
	selectedDay.value = Math.round(selectedDay.value)
	if (selectedDay.value < 1) {
		selectedDay.value = 1
	} else if (selectedDay.value > totalDays) {
		selectedDay.value = totalDays
	}

	const tempDate = setDayOfYear(
		new Date(Date.UTC(selectedYear.value, 0, 1, 0, 0, 0)),
		selectedDay.value,
	)
	model.value = new Date(
		Date.UTC(
			tempDate.getFullYear(),
			tempDate.getMonth(),
			tempDate.getDate(),
			0,
			0,
			0,
		),
	)
	console.log(`Just set model to ${model.value.toISOString()}`)
}

const needleDrag = (event: MouseEvent) => {
	const container = containerRef.value
	if (container) {
		const rect = container.getBoundingClientRect()
		const offsetX = event.clientX - rect.left
		const percentage = offsetX / rect.width

		selectedDay.value = Math.max(Math.min(percentage, 1), 0) * totalDays
		const tempDate = setDayOfYear(
			new Date(Date.UTC(selectedYear.value, 0, 1, 0, 0, 0)),
			selectedDay.value,
		)
		model.value = new Date(
			Date.UTC(
				tempDate.getFullYear(),
				tempDate.getMonth(),
				tempDate.getDate(),
				0,
				0,
				0,
			),
		)
	}
}

const zoomToDays = (startDay: number, endDay: number, year: number) => {
	// TODO - get these right once the other zooming is working
	const totalDays = 366
	const span = endDay - startDay + 3
	const scale = totalDays / span
	const translate = -startDay - 3

	const wrapper = svgZoomWrapperRefs[year] // get this from `ref`
	console.log('zoomToDays', wrapper, wrapper.style)
	wrapper!.style.transform = `scaleX(${scale}) translateX(${translate}px)`
}

const isInZoomRange = (day: number) => {
	if (props.selectedEvent) {
		const zoomStart = getDayOfYear(props.selectedEvent.startDate)
		const zoomEnd = getDayOfYear(props.selectedEvent.endDate)
		return day >= zoomStart && day <= zoomEnd
	} else {
		return true
	}
}

function assignTimelinePositions(
	events: { times: Date[]; color: string; y: number; id: number }[],
	targetYear: number,
) {
	// console.log('assignTimelinePositions', events, targetYear)
	// Filter to events active at any point in the target year
	const filtered = events.filter((e) => {
		return (
			e.times[0].getFullYear() <= targetYear &&
			e.times[e.times.length - 1].getFullYear() >= targetYear
		)
	})

	// Convert to day-of-year bounds within the year
	const sliced = filtered.map((e) => {
		const startDay =
			e.times[0].getFullYear() < targetYear ? 1 : getDayOfYear(e.times[0])

		const endDay =
			e.times[e.times.length - 1].getFullYear() > targetYear
				? (new Date(targetYear, 11, 31).getTime() -
						new Date(targetYear, 0, 0).getTime()) /
					86400000
				: getDayOfYear(e.times[e.times.length - 1])

		return {
			...e,
			startX: startDay,
			endX: endDay,
		}
	})

	// Assign y-levels using greedy algorithm
	const activeRows: any = [] // each: { endX, y }
	let nextY = 0

	const result = sliced
		.sort((a, b) => a.startX - b.startX)
		.map((event, idx) => {
			// Reclaim rows that are now free
			const usedYs = new Set()
			for (let row of activeRows) {
				if (row.endX >= event.startX) {
					usedYs.add(row.y)
				}
			}

			let y = 0
			while (usedYs.has(y)) y++
			activeRows.push({ endX: event.endX, y })
			event.y = y
			event.color = catScheme[event.id % catScheme.length]
			return event
		})

	return result
}

const scaleY = 0.05
const positionY = (y: number) => {
	if (y % 2 === 0) {
		return -scaleY * y
	} else {
		return scaleY * (y + 1)
	}
}
</script>

<template>
	<div class="time-reel">
		<div
			class="year-grid-container"
			ref="containerRef"
			:style="{ height: `${yearHeight * rowsToShow}px` }"
			v-on:scrollend="onScrollEnd"
		>
			<div class="year-grid">
				<div
					v-for="year in years"
					:key="year"
					class="year-row"
					:class="{ zoom: props.zoom }"
					:style="{ height: `${yearHeight}px` }"
				>
					<div class="year-label">{{ year }}</div>
					<div
						class="day-cell"
						v-for="day in days"
						:key="day"
						:class="{ even: isEvenMonth(day), shrunk: !isInZoomRange(day) }"
					></div>
					<div
						class="svg-zoom-wrapper"
						:ref="(el) => (el ? svgZoomWrapperRefs[year] = el as HTMLElement : null)"
						style=""
					>
						<svg
							class="year-overlay"
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 -1 366 2"
							preserveAspectRatio="none"
							pointer-events="none"
						>
							<rect
								v-for="event in assignTimelinePositions(
									props.events as any[],
									year,
								)"
								:x="event.startX"
								:width="event.endX - event.startX"
								:y="positionY(event.y)"
								:height="scaleY"
								:fill="event.color"
								:stroke="event.color"
								:stroke-width="0.8 * scaleY"
							></rect>
						</svg>
					</div>
				</div>
			</div>
		</div>
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
					:style="`left: ${(100 * selectedDay) / 366.0}%;`"
					@mousedown="startDrag"
				>
					<div class="line" />
					<div class="label" :class="{ hidden: !isDragging }">
						<p>{{ dayStr(selectedDay) }}</p>
					</div>
				</div>
				<p class="jan">{{ $l.months.jan }}</p>
				<p class="feb">{{ $l.months.feb }}</p>
				<p class="mar">{{ $l.months.mar }}</p>
				<p class="apr">{{ $l.months.apr }}</p>
				<p class="may">{{ $l.months.may }}</p>
				<p class="jun">{{ $l.months.jun }}</p>
				<p class="jul">{{ $l.months.jul }}</p>
				<p class="aug">{{ $l.months.aug }}</p>
				<p class="sep">{{ $l.months.sep }}</p>
				<p class="oct">{{ $l.months.oct }}</p>
				<p class="nov">{{ $l.months.nov }}</p>
				<p class="dec">{{ $l.months.dec }}</p>
			</div>
			<div
				class="highlight-row fade-bottom"
				:style="`flex: 0 0 calc( 0.5 * ( 100% - ( 100% / ${rowsToShow} ) )`"
			></div>
		</div>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.scss' as *;

$margin: 0 0.5rem;
.time-reel {
	position: relative;
}

.year-grid-container {
	margin: $margin;
	border: 1px solid #ccc;
	position: relative;
	overflow-y: scroll;
	width: 100%;
	padding: 0;
}

.year-grid {
	display: flex;
	flex-direction: column;

	.year-row {
		display: flex;
		position: relative;
		transition: all $animTime ease-in-out;
		// border: 1px solid red;

		&.zoom {
			transform: translateY(-100%);
		}

		.year-label {
			position: absolute;
			color: #888888;
			font-weight: bold;
			font-size: 0.75rem;
			pointer-events: none;
			user-select: none;
		}

		.day-cell {
			flex: 1 0 auto;
			min-width: 0;
			background-color: #f9f9f9;
			height: 100%;
			overflow: visible;
			&.even {
				background-color: #f0f0f0;
			}
			p {
				color: black;
			}
		}
	}
}

.svg-zoom-wrapper {
	overflow: hidden;
	width: 100%;
	transform-origin: left center;
	transition: transform 0.3s ease;
}

.year-overlay {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
	z-index: 1;
	transition: all $animTime ease-in-out;

	svg {
		transition: all $animTime ease-in-out;
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

	$fadeColor: #aaaaaa;

	.highlight-row {
		transition: all $animTime ease-in-out;
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
