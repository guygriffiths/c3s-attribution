<script setup lang="ts">
import { computed, watch, ref, toRaw } from 'vue'
import * as d3 from 'd3'

import CalendarIcon from '@/components/util/CalendarIcon.vue'
import Histogram from '@/components/util/Histogram.vue'
import { useStore } from '@/store/store'
import {
	useStore as useEventStore,
	intensityForValue,
} from '@/store/eventStore'
import {
	IconDimensions,
	IconGridDots,
	IconTemperature,
	IconTemperaturePlus,
	IconTemperatureMinus,
} from '@tabler/icons-vue'
import { niceNumber } from '@/lib/utils'
import { getBins } from '@/lib/histo-utils'
import { dateStr } from '@/lib/time-utils'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
const store = useStore()
const eventStore = useEventStore()

const props = defineProps<{
	selectedEvent: ExtremeEventFull | null
	selectedIndex: number
}>()

const selectedEvent = computed(() =>
	props.selectedEvent !== null
		? props.selectedEvent
		: ({
				id: '',
				times: [],
				duration: 0,
				regions: [],
				total_region: [],
				bbox: [-180, -90, 180, 90],
				max_value: 0,
				mean_value: 0,
				min_value: 0,
				total_area: 0,
				pixel_count: 0,
				pixel_set: [],
				ocean_only: false,
				color: '',
				event_type: 'hot',
				slices: [],
				values: [],
				centroids: [],
				areas: [],
				max_values: [],
				mean_values: [],
				min_values: [],
				pixel_max_values: [],
			} as ExtremeEventFull),
)
const days = computed(() => selectedEvent.value.times || [])

const eventType = computed(() => selectedEvent.value.event_type || 'hot')

const dayBins = ref<Record<number, any>>({})
// const xmin = ref(0)
// const xmax = ref(1)
const maxcount = ref(0)
const minmaxIntensities = computed(() => {
	return [
		intensityForValue(selectedEvent.value.min_value, eventType.value === 'hot'),
		intensityForValue(selectedEvent.value.max_value, eventType.value === 'hot'),
	]
})
const xmax = computed(() => {
	return Math.max(...minmaxIntensities.value)
})
const xmin = computed(() => {
	return Math.min(...minmaxIntensities.value)
})
const peakExtremeVals = ref<number[]>([])
watch(
	() => props.selectedEvent,
	(newVal) => {
		// recompute bins when event changes
		// console.log(
		// 	'Recomputing bins for new selected event',
		// 	selectedEvent.value,
		// 	days.value,
		// )
		if (newVal === null) return

		const newBins: any = {}
		let localCount = 0
		// let minVal = Infinity
		peakExtremeVals.value = []
		for (let i = 0; i < days.value.length; i++) {
			const day = days.value[i]
			const data = []
			if (newVal.values) {
				const vs = toRaw(newVal.values)
				try {
					data.push(
						...vs[i].map((v) =>
							intensityForValue(v, eventType.value === 'hot'),
						),
					)
				} catch {
					// Happens at initialisation before full event data loaded
				}
			}

			const bins = getBins(
				data,
				data.map(() => eventType.value),
				xmin.value,
				xmax.value,
				10,
				false,
			)
			// console.log('Computed bins for day', day, data, bins)
			localCount = Math.max(localCount, d3.max(bins, (d) => d.count) || 0)
			// if (newVal.min_values && newVal.min_values[i]) {
			// 	minVal = Math.min(minVal, newVal.min_values[i])
			// }
			if (newVal && newVal.max_values && newVal.min_values) {
				peakExtremeVals.value[i] =
					eventType.value === 'hot'
						? intensityForValue(newVal.max_values[i], true)
						: intensityForValue(newVal.min_values[i], false)
			}
			newBins[day] = bins
		}
		maxcount.value = Math.ceil(localCount * 1.05)
		dayBins.value = newBins
		// console.log(maxcount.value, xmin.value, xmax.value)
	},
	{ immediate: true },
)
const histogramData = computed(() => {
	const day = days.value[props.selectedIndex]
	// console.log('recalculating histogram data for day', day, dayBins.value[day])
	return dayBins.value[day] || []
})
const meanVal = computed(() => {
	try {
		return intensityForValue(
			selectedEvent.value.mean_values[props.selectedIndex],
			eventType.value === 'hot',
		)
	} catch {
		return 0
	}
})
const peakExtremeVal = computed(() => {
	try {
		return peakExtremeVals.value[props.selectedIndex] ?? 0
	} catch {
		return 0
	}
})
const size = computed(() => {
	try {
		selectedEvent.value.areas![props.selectedIndex] ?? 0
		return selectedEvent.value.areas![props.selectedIndex]
	} catch {
		return 0
	}
})
</script>

<template>
	<div class="event-day-panel-root">
		<div class="loading" v-if="store.eventSoftLoadingCount > 0">
			<div class="spinner-container">
				<div class="spinner-ring"></div>
				<div class="spinner-ring-inner"></div>
			</div>
		</div>
		<div class="flex-wrapper">
			<div class="chart">
				<div class="chart-xaxis">
					<Histogram
						:data="histogramData"
						:bins="dayBins[days[selectedIndex]]"
						:xmin="xmin"
						:xmax="xmax"
						:types="histogramData.map(() => eventType)"
						:yMaxCount="maxcount"
						:title="$l.pixelDistDaily"
					/>
					<div class="axis">
						<div class="label mono">
							{{ niceNumber(xmin) }}
						</div>
						<span class="unit-icon" v-tooltip="$l.temperature">
							<IconTemperaturePlus
								class="icon"
								aria-hidden="true"
								:class="{ [eventType]: true }"
								v-if="eventType === 'hot'"
							/>
							<IconTemperatureMinus
								class="icon"
								aria-hidden="true"
								:class="{ [eventType]: true }"
								v-else
							/>
						</span>
						<div class="label mono">
							{{ niceNumber(xmax) }}
						</div>
					</div>
				</div>
				<div class="axis">
					<div class="label mono">
						{{ 0 }}
					</div>
					<span class="units icon" v-tooltip="$l.pixelCount"
						><IconGridDots aria-hidden="true"
					/></span>
					<div class="label mono">
						{{ maxcount }}
					</div>
				</div>
			</div>
			<div class="day-info">
				<div class="info-row header">
					<CalendarIcon
						:size="24"
						:date="
							new Date(selectedEvent.times[props.selectedIndex] || 0).getDate()
						"
					/>
					<span class="mono">
						{{
							dateStr(new Date(selectedEvent.times[props.selectedIndex] || 0))
						}}
					</span>
				</div>
				<div
					class="info-row"
					v-tooltip="eventType === 'hot' ? $l.maxTempDaily : $l.minTempDaily"
				>
					<IconTemperaturePlus
						v-if="eventType === 'hot'"
						class="icon"
						:class="[eventType]"
						aria-hidden="true"
					/>
					<IconTemperatureMinus
						v-else
						class="icon"
						:class="[eventType]"
						aria-hidden="true"
					/>
					<span class="value mono"
						>{{ niceNumber(peakExtremeVal || 0) }}&nbsp;{{
							eventType === 'hot'
								? eventStore.heatIntensityUnits
								: eventStore.coldIntensityUnits
						}}</span
					>
				</div>
				<div class="info-row" v-tooltip="$l.meanTempDaily">
					<IconTemperature class="icon" aria-hidden="true" />
					<span class="value mono"
						>{{ niceNumber(meanVal) }}&nbsp;{{
							eventType === 'hot'
								? eventStore.heatIntensityUnits
								: eventStore.coldIntensityUnits
						}}</span
					>
				</div>
				<div class="info-row" v-tooltip="$l.sizeDaily">
					<IconDimensions class="icon" />
					<span class="value mono"
						>{{ niceNumber(size) }}&nbsp;{{ eventStore.sizeUnits }}</span
					>
				</div>
			</div>
		</div>
		<slot></slot>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.event-day-panel-root {
	position: relative;
	container: event-day-panel / size;

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

	.flex-wrapper {
		width: 100%;
		height: 100%;

		display: flex;
		flex-direction: row;
		gap: 0.5rem;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.5rem;

		.chart {
			width: 100%;
			display: flex;
			flex-direction: row;
			max-height: 100%;
			flex: 1 1 auto;
			height: 100%;

			.chart-xaxis {
				display: flex;
				flex-direction: column;
				align-items: center;
				justify-content: center;

				flex: 0 1 calc(100% - 1.5rem); /* allow shrinking */

				position: relative;
				display: flex;
				align-items: stretch; /* default, just in case */
				justify-content: center;
				min-height: 0; /* crucial for flex children that need to shrink */
				height: 100%; /* let flex handle it */
				max-height: calc(100% - 0.5rem);

				.histogram-root {
					flex: 0 1 calc(100% - 2.5rem);
					height: calc(100% - 2.5rem);
					background: var(--panel-bg);
					box-shadow: inset 2px 2px 8px rgba(0, 0, 0, 0.2);
				}

				.axis {
					flex-direction: row;
					flex: 0 0 2.5rem;
					max-height: 2.5rem;
					width: 100%;
				}
			}

			.axis {
				height: calc(100% - 2.5rem);
				.label {
					flex: 0 1 auto;
				}
			}
		}

		.day-info {
			flex: 0 0 auto;
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
			min-width: 8rem;

			.info-row {
				display: flex;
				flex-direction: row;
				align-items: center;
				gap: 0.5rem;

				&.header {
					font-size: 1rem;
					font-weight: bold;
					border-bottom: 1px solid var(--divider);
					padding-bottom: 0.25rem;
				}

				.icon {
					flex: 0 0 auto;
					width: 1.5rem;
					height: 1.5rem;
					color: var(--text-secondary);
				}

				.value {
					flex: 1 1 auto;
					text-align: right;
				}
			}
		}
	}
}

@container event-day-panel (min-height: 300px) {
	.event-day-panel-root {
		.flex-wrapper {
			flex-direction: column-reverse;
			justify-content: space-between;
			gap: 1.5rem;
			padding-bottom: 0;

			.day-info {
				flex-direction: row;
				flex-wrap: wrap;
				justify-content: space-between;
				gap: 0.25rem 1rem;
				min-width: auto;
				padding-top: 0.5rem;

				.header {
					flex: 0 0 100%;
					span {
						text-align: center;
					}
					display: flex;
					justify-content: center;
				}
			}
		}
	}
}
</style>
