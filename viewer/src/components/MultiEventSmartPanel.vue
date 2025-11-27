<script setup lang="ts">
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import Histogram from './util/Histogram.vue'
import ScatterPlot from './util/ScatterPlot.vue'
import EventRanker from './util/EventRanker.vue'
import Panel from './util/Panel.vue'
import {
	IconLayersIntersect,
	IconStopwatch,
	IconDimensions,
	IconTemperature,
	IconCalendar,
} from '@tabler/icons-vue'
import { ref, watch, computed } from 'vue'
import { getBins } from '@/lib/histo-utils'
import { niceNumber } from '@/lib/utils'

const store = useStore()
const eventStore = useEventStore()
const timeStore = useTimeStore()
const scrollerRef = ref<HTMLElement | null>(null)
const medalsSubRef = ref<HTMLElement | null>(null)
const scatterSubRef = ref<HTMLElement | null>(null)

const props = defineProps<{
	eventsOfInterest: ExtremeEvent[]
}>()

console.log('TODO: scrollTo on resize, MultiEventPanel')
watch(
	() => store.showAnalytics,
	(newVal) => {
		if (newVal) {
			scatterSubRef.value?.scrollIntoView({
				behavior: 'smooth',
				block: 'start',
			})
			// scrollerRef.value?.scrollTo({ top: scrollerRef.value.scrollHeight, behavior: 'smooth' })
		} else {
			// medalsSubRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
			scrollerRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
		}
	},
)

const xmin = computed(() => {
	return store.focusVariable === 'duration'
		? eventStore.durationRange[0]
		: store.focusVariable === 'size'
			? eventStore.sizeRange[0]
			: eventStore.intensityRange[0]
})
const xmax = computed(() => {
	const xmax =
		store.focusVariable === 'duration'
			? Math.max(eventStore.durationP90 || 0, 13) || eventStore.durationRange[1]
			: store.focusVariable === 'size'
				? eventStore.sizeP90 || eventStore.sizeRange[1]
				: Math.max(
						eventStore.heatIntensityRange[1] || 0,
						eventStore.coldIntensityRange[1] || 0,
					)
	if (eventStore.selectedEvent !== null)
		return Math.max(xmax, valueForEvent.value || 0)
	return xmax
})
const valueForEvent = computed(() => {
	if (!eventStore.selectedEvent) return null
	return store.focusVariable === 'duration'
		? eventStore.durationForEvent(eventStore.selectedEvent)
		: store.focusVariable === 'size'
			? eventStore.sizeForEvent(eventStore.selectedEvent)
			: eventStore.intensityForEvent(eventStore.selectedEvent)
})
const eventsOfInterest = computed(() => {
	return store.focusVariable === 'duration'
		? props.eventsOfInterest.map(eventStore.durationForEvent)
		: store.focusVariable === 'size'
			? props.eventsOfInterest.map(eventStore.sizeForEvent)
			: props.eventsOfInterest.map(eventStore.intensityForEvent)
})
const types = computed(() => {
	return props.eventsOfInterest.map((e) => e.event_type)
})
const allHot = computed(() => {
	return props.eventsOfInterest.every((e) => e.event_type === 'hot')
})
const allCold = computed(() => {
	return props.eventsOfInterest.every((e) => e.event_type === 'cold')
})
const scatterY = ref<Variable>('intensity')
const cycleYVar = () => {
	// if (scatterY.value === 'intensity') {
	// 	scatterY.value = 'duration'
	// } else if (scatterY.value === 'duration') {
	// 	scatterY.value = 'size'
	// } else {
	// 	scatterY.value = 'intensity'
	// }
	if (scatterY.value === 'intensity') {
		if (store.focusVariable === 'duration') scatterY.value = 'size'
		else scatterY.value = 'duration'
	} else if (scatterY.value === 'duration') {
		if (store.focusVariable === 'size') scatterY.value = 'intensity'
		else scatterY.value = 'size'
	} else {
		if (store.focusVariable === 'intensity') scatterY.value = 'duration'
		else scatterY.value = 'intensity'
	}
}
const ymin = computed(() => {
	return scatterY.value === 'intensity'
		? eventStore.intensityRange[0]
		: scatterY.value === 'duration'
			? eventStore.durationRange[0]
			: eventStore.sizeRange[0]
})
const ymax = computed(() => {
	const ymax =
		scatterY.value === 'intensity'
			? allHot.value
				? Math.max(eventStore.heatIntensityP90 || 0, 1)
				: allCold.value
					? Math.max(eventStore.coldIntensityP90 || 0, 1)
					: Math.max(
							eventStore.heatIntensityP90 || 0,
							eventStore.coldIntensityP90 || 0,
						) || eventStore.intensityRange[1]
			: scatterY.value === 'duration'
				? Math.max(eventStore.durationP90 || 0, 13) ||
					eventStore.durationRange[1]
				: eventStore.sizeP90 || eventStore.sizeRange[1]
	if (eventStore.selectedEvent !== null)
		return Math.max(ymax, valueForEvent.value || 0)

	if (scatterY.value === 'duration') {
		return eventStore.durationRange[1]
	}
	if (scatterY.value === 'size') {
		return eventStore.sizeRange[1]
	}
	if (scatterY.value === 'intensity') {
		return eventStore.intensityRange[1]
	}
	return ymax
})
const ydata = computed(() => {
	return scatterY.value === 'intensity'
		? props.eventsOfInterest.map((e) => eventStore.intensityForEvent(e))
		: scatterY.value === 'duration'
			? props.eventsOfInterest.map((e) => eventStore.durationForEvent(e))
			: props.eventsOfInterest.map((e) => eventStore.sizeForEvent(e))
})
const ids = computed(() => {
	return props.eventsOfInterest.map((e) => e.id)
})
const bins = computed(() => {
	const data = eventsOfInterest.value
	return getBins(data, types.value, xmin.value, xmax.value, 10)
})
const maxCount = computed(() => {
	return bins.value.reduce((max, bin) => Math.max(max, bin.count), 0)
})
watch(
	() => store.focusVariable,
	(newVal, oldVal) => {
		if (scatterY.value === newVal) {
			scatterY.value = oldVal
		}
	},
)
</script>
<template>
	<div class="multi-event-panel panel">
		<div class="scroller" ref="scrollerRef">
			<div class="chart">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">
							{{ 0 }}
						</div>
						<span class="units icon"><IconLayersIntersect /></span>
						<div class="label mono">
							{{ maxCount }}
						</div>
					</div>
					<Histogram
						:data="eventsOfInterest"
						:bins="bins"
						:nbins="10"
						:xmin="xmin"
						:xmax="xmax"
						:labelFunc="(v: number) => v.toFixed(0)"
						:units="'days'"
						:highlight-value="valueForEvent"
						:types="types"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono">
						{{ niceNumber(xmin) }}
					</div>
					<span class="units icon">
						<button @click="store.cycleSorts" class="cycle-sort-button glassy">
							<IconStopwatch v-if="store.focusVariable === 'duration'" />
							<IconDimensions v-else-if="store.focusVariable === 'size'" />
							<IconTemperature v-else />
						</button>
					</span>
					<div class="label mono">
						{{ niceNumber(xmax) }}
					</div>
				</div>
			</div>

			<div class="chart">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">{{ niceNumber(ymin) }}</div>
						<span class="units icon">
							<button @click="cycleYVar" class="cycle-sort-button glassy">
								<IconStopwatch v-if="scatterY === 'duration'" />
								<IconDimensions v-else-if="scatterY === 'size'" />
								<IconTemperature v-else />
							</button>
						</span>
						<div class="label mono">
							{{ niceNumber(ymax) }}
						</div>
					</div>
					<ScatterPlot
						:xdata="eventsOfInterest"
						:ydata="ydata"
						:types="types"
						:xmin="xmin"
						:xmax="xmax"
						:ymin="ymin"
						:ymax="ymax"
						:ids="ids"
						:highlightId="eventStore.selectedEventId"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono">
						{{ niceNumber(xmin) }}
					</div>
					<span class="units icon">
						<button @click="store.cycleSorts" class="cycle-sort-button glassy">
							<IconStopwatch v-if="store.focusVariable === 'duration'" />
							<IconDimensions v-else-if="store.focusVariable === 'size'" />
							<IconTemperature v-else />
						</button>
					</span>
					<div class="label mono">
						{{ niceNumber(xmax) }}
					</div>
				</div>
			</div>
			<div class="chart">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">{{ niceNumber(xmin) }}</div>
						<span class="units icon">
							<button
								@click="store.cycleSorts"
								class="cycle-sort-button glassy"
							>
								<IconStopwatch v-if="store.focusVariable === 'duration'" />
								<IconDimensions v-else-if="store.focusVariable === 'size'" />
								<IconTemperature v-else />
							</button>
						</span>
						<div class="label mono">
							{{ niceNumber(xmax) }}
						</div>
					</div>
					<ScatterPlot
						:xdata="props.eventsOfInterest.map((e) => e.times[0])"
						:ydata="eventsOfInterest"
						:types="types"
						:xmin="timeStore.startTime.getTime()"
						:xmax="timeStore.endTime.getTime()"
						:ymin="xmin"
						:ymax="xmax"
						:ids="ids"
						:highlightId="eventStore.selectedEventId"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono">
						{{ timeStore.startTime.toISOString().slice(0, 10) }}
					</div>
					<span class="units icon">
						<IconCalendar />
					</span>
					<div class="label mono">
						{{ timeStore.endTime.toISOString().slice(0, 10) }}
					</div>
				</div>
			</div>
		</div>
		<!-- <div class="buttons">
			<IconChartHistogram class="body" size="1.5rem" />
			<IconChartSankey class="tail" size="1.25rem" />
		</div> -->
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.buttons {
	position: absolute;
	bottom: 0.5rem;
	right: 0.5rem;
	display: flex;
	flex-direction: row;
	gap: 0rem;
}

.multi-event-panel {
	display: flex;
	flex-direction: column;
	padding: 0 0.125rem;

	.scroller {
		height: 100%;
		width: 100%;
		flex: 1 1 auto;

		display: flex;
		flex-direction: column;
		overflow-y: scroll;
		overflow-x: visible;
		// margin-bottom: 0.25rem;
		scroll-snap-type: y mandatory;
		justify-content: space-between;

		.chart {
			scroll-snap-align: center;
			flex: 0 0 calc(100% - 1.5rem);
			padding: 0.25rem;
			border: none;
			border-bottom: 1px solid var(--divider);
			width: 100%;
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
			justify-content: space-around;

			.yaxis-chart {
				flex: 1 1 auto;
				display: flex;
				flex-direction: row;
				justify-content: space-between;
				gap: 0.5rem;
				align-items: center;
			}

			.axis.horizontal {
				margin-left: 2.5rem;
				width: calc(100% - 2.5rem);
			}

			.histogram-root,
			.scatter-root {
				flex: 1 1 auto;
				// border: 1px solid blue;
				background: var(--panel-bg);
				padding: 0 0.5rem;
			}
		}
	}
}
</style>
<style>
.body {
	path:nth-child(2),
	path:nth-child(3),
	path:nth-child(4),
	path:nth-child(5) {
		display: none;
	}

	path:nth-child(6) {
		transform: translate(0, 2px);
	}
}

.tail {
	transform: translate(-6px, 7px) scaleY(0.8);
	path:nth-child(1),
	path:nth-child(2),
	path:nth-child(5) {
		display: none;
	}
}
</style>
