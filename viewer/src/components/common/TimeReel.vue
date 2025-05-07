<script setup lang="ts">
import { format, getDayOfYear, setDayOfYear } from 'date-fns'
import { ref, computed, defineModel, Ref, watch } from 'vue'
import { catScheme } from '@/store/store';

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
		default: () => [] as {startDate: Date; endDate: Date}[],
	},
})

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})

const containerRef = ref<HTMLDivElement | null>(null)
const needleRef = ref<HTMLDivElement | null>(null)

const yearHeight = 128
const totalDays = 366
const selectedDay = ref(getDayOfYear(model.value))
const selectedYear = ref(model.value.getFullYear())

const startYear = computed(() => props.start.getFullYear())
const endYear = computed(() => props.end.getFullYear())
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
	if (containerRef.value) {
		const scrollTop = containerRef.value.scrollTop
		const yearIndex = Math.round(scrollTop / yearHeight)
		const targetScrollTop = yearIndex * yearHeight
		containerRef.value.scrollTo({ top: targetScrollTop, behavior: 'smooth' })

		// +1 is because we are looking at 3 years and want the second one
		selectedYear.value = years.value[yearIndex + 1]
		model.value = setDayOfYear(
			new Date(selectedYear.value, 0, 1),
			selectedDay.value,
		)
	}
}

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
	model.value = setDayOfYear(
		new Date(selectedYear.value, 0, 1),
		selectedDay.value,
	)
}

const needleDrag = (event: MouseEvent) => {
	const container = containerRef.value
	if (container) {
		const rect = container.getBoundingClientRect()
		const offsetX = event.clientX - rect.left
		const percentage = offsetX / rect.width

		selectedDay.value = Math.max(Math.min(percentage, 1), 0) * totalDays
	}
}

function assignTimelinePositions(
	events: { startTime: Date; endTime: Date, color: string, y: number }[],
	targetYear: number,
) {
	// console.log('assignTimelinePositions', events, targetYear)
	// Filter to events active at any point in the target year
	const filtered = events.filter((e) => {
		return (
			e.startTime.getFullYear() <= targetYear &&
			e.endTime.getFullYear() >= targetYear
		)
	})

	// Convert to day-of-year bounds within the year
	const sliced = filtered.map((e) => {
		const startDay =
			e.startTime.getFullYear() < targetYear ? 1 : getDayOfYear(e.startTime)

		const endDay =
			e.endTime.getFullYear() > targetYear
				? (new Date(targetYear, 11, 31).getTime() -
						new Date(targetYear, 0, 0).getTime()) /
					86400000
				: getDayOfYear(e.endTime)

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
			event.color = catScheme[idx % catScheme.length]
			return event
		})

	return result
}

const scaleY = 0.025
const positionY = (y: number) => {
	if(y % 2 === 0) {
		return -0.025 * y
	} else {
		return 0.025 * (y+1)
	}
	return 0
}
</script>

<template>
	<div class="time-reel">
		<div
			class="time-reel-container"
			ref="containerRef"
			:style="{ height: `${yearHeight * 3}px` }"
			v-on:scrollend="onScrollEnd"
		>
			<div class="year-grid">
				<div
					v-for="year in years"
					:key="year"
					class="year-row"
					:style="{ height: `${yearHeight}px` }"
				>
					<div class="year-label">{{ year }}</div>
					<div
						class="day-cell"
						v-for="day in days"
						:key="day"
						:class="{ even: isEvenMonth(day) }"
					></div>
					<svg
						class="year-overlay"
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 -1 366 2"
						preserveAspectRatio="none"
						pointer-events="none"
					>
						<rect
							v-for="event in assignTimelinePositions(props.events as any[], year)"
							:x="event.startX"
							:width="event.endX - event.startX"
							:y="positionY(event.y)"
							:height="0.024"
							:fill="event.color"
						></rect>
					</svg>
				</div>
			</div>
		</div>
		<div class="year-highlights">
			<div class="highlight-row fade-top"></div>
			<div class="highlight-row highlight">
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
				<p class="jan">Jan</p>
				<p class="feb">Feb</p>
				<p class="mar">Mar</p>
				<p class="apr">Apr</p>
				<p class="may">May</p>
				<p class="jun">Jun</p>
				<p class="jul">Jul</p>
				<p class="aug">Aug</p>
				<p class="sep">Sep</p>
				<p class="oct">Oct</p>
				<p class="nov">Nov</p>
				<p class="dec">Dec</p>
			</div>
			<div class="highlight-row fade-bottom"></div>
		</div>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.scss' as *;

$margin: 0 0.5rem;
.time-reel {
	position: relative;
}

.time-reel-container {
	margin: $margin;
	border: 1px solid #ccc;
	position: relative;
	overflow-y: scroll;
}

.year-grid {
	display: flex;
	flex-direction: column;

	.year-row {
		display: flex;
		position: relative;
		// border: 1px solid black;

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

.year-overlay {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
	z-index: 1;
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

	$fadeColor: #aaaaaa;

	.highlight-row {
		flex: 0 0 33.33%;

		&.fade-top {
			pointer-events: none;
			background: linear-gradient(
				to top,
				rgba($fadeColor, 0.3),
				rgba($fadeColor, 1)
			);
			// background: #aaaaaa;
			// opacity: 0.5;
		}
		&.fade-bottom {
			pointer-events: none;
			background: linear-gradient(
				to bottom,
				rgba($fadeColor, 0.3),
				rgba($fadeColor, 1)
			);
			// background: #aaaaaa;
			// opacity: 0.5;
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
				border-top: 7px solid red;
				border-right: 7px solid transparent;
				border-left: 7px solid transparent;
				border-bottom: none;
				transform: translateX(-50%);

				.line {
					position: absolute;
					// left: 8px;
					width: 1px;
					height: 100%;
					background-color: red;
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
					transition: opacity 0.5s ease-in-out;

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
				// height: 100%;
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
