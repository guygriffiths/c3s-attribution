<script setup lang="ts">
import { computed, watch, onBeforeUnmount, onMounted, ref } from 'vue'
import * as d3 from 'd3'

import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import { IconDimensions, IconTemperatureMinus, IconTemperaturePlus } from '@tabler/icons-vue'
import { niceNumber } from '@/lib/utils'
import { dateStr } from '@/lib/time-utils'
import { useLabels } from '@/lib/labels'
import { circle } from 'leaflet'

const $l = useLabels()
const store = useStore()
const eventStore = useEventStore()
const timeStore = useTimeStore()
const props = defineProps<{ selectedEvent: ExtremeEventFull | null }>()
const emits = defineEmits<{
	(event: 'dateSelected', date: number): void
}>()

const days = computed(() => props.selectedEvent?.times || [])
const areaData = computed(() => eventStore.sizesForEvent(props.selectedEvent))
const intensityData = computed(() => {
	// console.log(
	// 	'Intensity data for event',
	// 	props.selectedEvent,
	// 	eventStore.intensitiesForEvent(props.selectedEvent),
	// )
	return eventStore.intensitiesForEvent(props.selectedEvent)
})

const chartTopMargin = 0

const svgRef = ref<SVGSVGElement | null>(null)
const width = ref(100)
const height = ref(200)

// Scales
const xScale = computed(() => {
	const sideMargin = (0.5 * width.value) / (days.value.length + 1)
	return d3
		.scaleBand()
		.domain(days.value.map((_, i) => i.toString()))
		.range([sideMargin, width.value - sideMargin])
		.padding(0)
})

const sizeScale = computed(() => {
	// console.log('Area data for sizeScale:', areaData.value)
	return d3
		.scaleLinear()
		.domain([0, d3.max(areaData ? areaData.value : []) || 1])
		.range([height.value - 3, chartTopMargin + 3])
})
const intensityScale = computed(() =>
	d3
		.scaleLinear()
		.domain([
			d3.min(intensityData.value) || 0,
			d3.max(intensityData.value) || 1,
		])
		.range([height.value - 5, chartTopMargin + 5]),
)

const selectedIndex = computed(() => {
	if (!props.selectedEvent) return -1
	const selectedTime = timeStore.selectedTime
	return props.selectedEvent.times.findIndex(
		(d) => d === selectedTime.getTime(),
	)
})

onMounted(() => {
	const observer = new ResizeObserver((entries) => {
		for (const entry of entries) {
			width.value = entry.contentRect.width
			height.value = entry.contentRect.height
		}
		// console.log('SVG resized:', entries, width.value, height.value)
	})
	if (!svgRef.value) return
	observer.observe(svgRef.value)

	onBeforeUnmount(() => observer.disconnect())
})

watch(
	() => [
		props.selectedEvent,
		areaData.value,
		intensityData.value,
		svgRef.value,
	],
	() => {
		// console.log('EventGraphs: event or areaData changed')
		// Reset scales when event changes
		width.value = svgRef.value?.clientWidth || 100
		height.value = svgRef.value?.clientHeight || 100
	},
)

const eventType = computed(() => props.selectedEvent?.event_type || 'unknown')
</script>

<template>
	<div class="event-graphs-root">
		<div class="loading" v-if="store.eventSoftLoadingCount > 0">
			<div class="spinner-container">
				<div class="spinner-ring"></div>
				<div class="spinner-ring-inner"></div>
			</div>
		</div>
		<div class="chart">
			<h1 class="chart-title">
				{{ $l.eventIntensityTS }}
			</h1>
			<div class="axis">
				<div class="label mono">
					{{ niceNumber(intensityScale.domain()[0]) }}
				</div>
				<span class="unit-icon"
					>
					<IconTemperaturePlus v-if="selectedEvent?.event_type === 'hot'" class="icon" :class="{ [eventType]: true }" />
					<IconTemperatureMinus v-else class="icon" :class="{ [eventType]: true }" />
					
					{{
						selectedEvent?.event_type === 'hot'
							? eventStore.heatIntensityUnits
							: eventStore.coldIntensityUnits
					}}
					</span
				>
				<div class="label mono">
					{{ niceNumber(intensityScale.domain()[1]) }}
				</div>
			</div>
			<svg class="intensity-chart" ref="svgRef" id="event-graph-width-el">
				<defs>
					<filter id="egBarShadow" height="130%">
						<feDropShadow
							dx="1"
							dy="1"
							stdDeviation="1"
							flood-color="rgba(0, 0, 0, 0.1)"
						/>
					</filter>
				</defs>
				<rect
					v-if="selectedIndex >= 0"
					:x="xScale(selectedIndex.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					class="graph-bg selected"
				/>
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
						<circle 
							v-for="(value, i) in intensityData" 
							:key="i"
							:cx="xScale(i.toString())! + xScale.bandwidth() / 2"
							:cy="intensityScale(value)"
							r="5"
							:class="{
								selected: i === selectedIndex,
								[eventType]: true,
							}"
							class="line-point"
							@click="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							@keydown.space.prevent="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							v-tooltip="dateStr(new Date(props.selectedEvent?.times[i] || 0)) + ': ' + niceNumber(value) + ' ' + (selectedEvent?.event_type === 'hot' ? eventStore.heatIntensityUnits : eventStore.coldIntensityUnits)"	/>
					</template>
				</g>
			</svg>
		</div>
		<div class="spacer"></div>
		<div class="chart">
			<h1 class="chart-title">
				{{ $l.eventSizeTS }}
			</h1>
			<div class="axis">
				<div class="label mono">{{ niceNumber(sizeScale.domain()[0]) }}</div>
				<span class="unit-icon"
					><IconDimensions class="icon" :class="{ [eventType]: true }" />{{
						eventStore.sizeUnits
					}}</span
				>
				<div class="label mono">{{ niceNumber(sizeScale.domain()[1]) }}</div>
			</div>
			<svg class="size-chart">
				<defs>
					<filter id="egBarShadow" height="130%">
						<feDropShadow
							dx="1"
							dy="1"
							stdDeviation="1"
							flood-color="rgba(0, 0, 0, 0.1)"
						/>
					</filter>
				</defs>
				<rect
					v-if="selectedIndex >= 0"
					:x="xScale(selectedIndex.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					class="graph-bg selected"
				/>

				<g>
					<template v-for="(value, i) in areaData" :key="i">
						<rect
							:x="xScale(i.toString())"
							:y="sizeScale(value)"
							:width="xScale.bandwidth() - 0.5"
							:height="height - sizeScale(value)"
							:class="{
								selected: i === selectedIndex,
								[eventType]: true,
							}"
							vector-effect="non-scaling-stroke"
							class="area-bar"
							filter="url(#egBarShadow)"
							@click="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							@keydown.space.prevent="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							v-tooltip="dateStr(new Date(props.selectedEvent?.times[i] || 0)) + ': ' + niceNumber(value) + ' ' + eventStore.sizeUnits"
						</rect>
					</template>
				</g>
			</svg>
		</div>
		<slot></slot>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.event-graphs-root {
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	padding: 0.5rem;

	.loading {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: var(--panel-bg-night);
		background-image: var(--panel-bg);
		z-index: 10;
	}

	&.loading {
		flex: 0 0 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.spacer {
		margin: 0.25rem 0;
		width: 100%;
		flex: 0 0 1px;
		background-color: var(--divider);
	}

	.chart {
		z-index: 0;

		flex: 0 1 calc(50% - 0.5rem); /* allow shrinking */
		max-height: calc(50% - 0.5rem);

		width: 100%; /* let flex handle it */
		min-width: 0; /* crucial for flex children that need to shrink */
		position: relative;
		display: flex;
		flex-direction: row;
		align-items: stretch; /* default, just in case */
		justify-content: center;

		.axis {
			flex: 1 0 2.5rem;
			height: 100%;
			display: flex;
			flex-direction: column-reverse;
			justify-content: space-between;
			align-items: center;
			font-size: 0.85rem;

			.label {
				user-select: none;
				color: var(--text-secondary);
				flex: 0 0 auto;
			}

			.icon {
				flex: 0 0 1.25rem;
				width: 1.25rem;
				height: 1.25rem;
				margin: 0.25rem 0;

				display: flex;
				align-items: center;
				justify-content: center;

				&.hot {
					color: var(--theme-hot-primary);
				}
				&.cold {
					color: var(--theme-cold-primary);
				}
			}
		}

		.size-chart,
		.intensity-chart {
			flex: 1 1 75%;
			background: var(--panel-bg);
			box-shadow: inset 2px 2px 8px rgba(0, 0, 0, 0.2);
			// display: block;
			// width: 100%; /* remove !important */
			// height: 100%; /* optional: depends on parent */
			// max-width: 100%;
			// max-height: 100%;
		}
	}
}

.size-chart,
.intensity-chart {
	font-family: sans-serif;
	font-size: 12px;
	user-select: none;

	.area-bar {
		cursor: pointer;
		&.hot {
			fill: var(--theme-hot-primary);
		}
		&.cold {
			fill: var(--theme-cold-primary);
		}
		&.selected {
			fill: var(--primary-glass-shine);
			&.hot {
				fill: var(--theme-hot-primary-glass-shine);
			}
			&.cold {
				fill: var(--theme-cold-primary-glass-shine);
			}
		}
	}

	.line-point {
		cursor: default;
		stroke: none;
		opacity: 0;
		&.selected {
			cursor: pointer;
			opacity: 1;
			r:4;
			fill: var(--primary-glass-shine);
			&.hot {
				fill: var(--theme-hot-primary-glass-shine);
			}
			&.cold {
				fill: var(--theme-cold-primary-glass-shine);
			}
		}
	}

	.intensity-line {
		&.hot {
			stroke: var(--theme-hot-primary);
		}
		&.cold {
			stroke: var(--theme-cold-primary);
		}
	}

	.graph-bg {
		fill: white;
		cursor: pointer;
	}
}
</style>
