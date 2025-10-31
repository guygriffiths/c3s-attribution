<script setup lang="ts">
import { computed, ComputedRef, onBeforeUnmount, onMounted, ref } from 'vue'
import * as d3 from 'd3'

import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import { IconDimensions, IconTemperature } from '@tabler/icons-vue'
import scssVars from '@/assets/styles/scssVars.module.scss'

const eventStore = useEventStore()
const timeStore = useTimeStore()
const props = defineProps<{ selectedEvent: ExtremeEventFull | null }>()
const emits = defineEmits<{
	(event: 'dateSelected', date: Date): void
}>()

const days = computed(() => props.selectedEvent?.times || [])
const areaData = computed(() => eventStore.sizesForEvent(props.selectedEvent))
const intensityData = computed(() =>
	eventStore.intensitiesForEvent(props.selectedEvent),
)

const chartTopMargin = 20

const svgRef = ref<SVGSVGElement | null>(null)
const width = ref(800)
const height = ref(400)

// Scales
const xScale = computed(() => {
	const sideMargin = (0.5 * width.value) / (days.value.length + 1)
	return d3
		.scaleBand()
		.domain(days.value.map((_, i) => i.toString()))
		.range([sideMargin, width.value - sideMargin])
		.padding(0)
})

const sizeScale = computed(() =>
	d3
		.scaleLinear()
		.domain([0, d3.max(areaData.value) || 1])
		.range([height.value - 2, chartTopMargin]),
)
const intensityScale = computed(() =>
	d3
		.scaleLinear()
		.domain([0, d3.max(intensityData.value) || 1])
		.range([height.value, chartTopMargin]),
)

const selectedIndex = computed(() => {
	if (!props.selectedEvent) return -1
	const selectedTime = timeStore.selectedTime
	return props.selectedEvent.times.findIndex(
		(d) => d.getTime() === selectedTime.getTime(),
	)
})

onMounted(() => {
	if (!svgRef.value) return

	const observer = new ResizeObserver((entries) => {
		for (const entry of entries) {
			width.value = entry.contentRect.width
			height.value = entry.contentRect.height
		}
	})
	observer.observe(svgRef.value)

	onBeforeUnmount(() => observer.disconnect())
})

const eventType = computed(() => props.selectedEvent?.event_type || 'unknown')
</script>

<template>
	<div class="event-graphs-root">
		<IconDimensions class="size-icon" :class="{ [eventType]: true }" />
		<IconTemperature class="intensity-icon" :class="{ [eventType]: true }" />
		<svg class="graph-container" ref="svgRef">
			<!-- <transition-group
			name="graph-bg-transition"
			tag="g"
			:style="{ transform: 'scaleY(-1) translateY(-100%)' }"
		> -->
			<rect
				:x="xScale('0') - xScale.bandwidth()"
				:y="0"
				:width="xScale.bandwidth()"
				:height="height * 3"
				class="graph-bg"
			/>
			<rect
				:x="xScale.range()[1]"
				:y="0"
				:width="xScale.bandwidth()"
				:height="height * 3"
				class="graph-bg"
			/>
			<template v-for="(day, i) in days" :key="day">
				<rect
					:x="xScale(i.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					class="graph-bg"
					:class="{ odd: i % 2 === 1, selected: i === selectedIndex }"
					@click="emits('dateSelected', day)"
				/>
			</template>
			<!-- </transition-group> -->

			<g>
				<template v-for="(value, i) in areaData" :key="i">
					<rect
						:x="xScale(i.toString())"
						:y="sizeScale(value)"
						:width="xScale.bandwidth()"
						:height="height - sizeScale(value)"
						:class="{
							selected: i === selectedIndex,
							[eventType]: true,
						}"
						stroke="white"
						:stroke-width="0.5"
						vector-effect="non-scaling-stroke"
						class="area-bar"
					/>
				</template>
			</g>

			<!-- Peak and Mean Value Line Chart -->
			<g>
				<template v-if="intensityData.length">
					<polyline
						class="intensity-line"
						:class="{ [eventType]: true }"
						fill="none"
						stroke-width="2"
						:points="
							intensityData
								.map(
									(value, i) =>
										`${xScale(i.toString())! + xScale.bandwidth() / 2},${intensityScale(
											value,
										)}`,
								)
								.join(' ')
						"
					/>
				</template>
			</g>
		</svg>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.event-graphs-root {
	width: 100%;
	height: 100%;
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;

	.size-icon {
		width: min(25%, 2rem);
		height: auto;
		color: var(--primary-hover);
		opacity: 1;
		position: absolute;
		top: 4px;
		left: 8px;
		pointer-events: none;
		z-index: 10;

		&.hot {
			color: var(--theme-hot-primary-hover);
		}
		&.cold {
			color: var(--theme-cold-primary-hover);
		}
	}

	.intensity-icon {
		width: min(25%, 2rem);
		height: auto;
		color: var(--primary-muted);
		opacity: 1;
		position: absolute;
		top: 4px;
		right: 4px;
		pointer-events: none;
		&.hot {
			color: var(--theme-hot-primary-muted);
		}
		&.cold {
			color: var(--theme-cold-primary-muted);
		}
	}

	.graph-container {
		width: 100%;
		height: 100%;
		z-index: 0;
		flex: 0 0 100%;
	}
}

svg {
	font-family: sans-serif;
	font-size: 12px;
	user-select: none;
	width: 100%;
	height: 100%;

	.area-bar {
		&.hot {
			fill: var(--theme-hot-primary-hover);
		}
		&.cold {
			fill: var(--theme-cold-primary-hover);
		}
	}

	.intensity-line {
		&.hot {
			stroke: var(--theme-hot-primary-muted);
		}
		&.cold {
			stroke: var(--theme-cold-primary-muted);
		}
	}

	rect.selected {
		fill: var(--highlight);
	}

	.graph-bg {
		cursor: pointer;
		fill: none;
		fill: var(--panel-bg);

		&.selected {
			fill: var(--panel-bg-alt);
		}
	}

	.graph-bg-transition-enter-active {
		transition: all $animTime ease-in-out calc($animTime + $settleTime);
	}
	.graph-bg-transition-leave-active {
		transition: all $animTime ease-in-out;
	}
	.graph-bg-transition-enter-from,
	.graph-bg-transition-leave-to {
		height: 0;
	}
	.graph-bg-transition-enter-to,
	.graph-bg-transition-leave-from {
		height: 100%;
	}
}
text {
	fill: #444;
	font-weight: bold;
}
</style>
