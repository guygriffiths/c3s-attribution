<script setup lang="ts">
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import Histogram from './util/Histogram.vue'
import ScatterPlot from './util/ScatterPlot.vue'
import EventRanker from './util/EventRanker.vue'
import Panel from './util/Panel.vue'
import {
	IconArrowDown,
	IconArrowUp,
	IconAward,
	IconChartBar,
	IconChartScatter,
	IconClockHour4,
	IconDimensions,
	IconFileAnalytics,
	IconHourglassHigh,
	IconMapStar,
	IconReportAnalytics,
	IconTemperature,
	IconTemperatureSnow,
	IconTemperatureSun,
	IconStopwatch,
	IconChevronRight,
	IconChevronLeft,
} from '@tabler/icons-vue'
import { ref, watch, computed } from 'vue'

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
const ymin = computed(() => {
	return store.focusVariable === 'intensity'
		? eventStore.durationRange[0]
		: store.focusVariable === 'duration'
			? eventStore.sizeRange[0]
			: eventStore.intensityRange[0]
})
const ymax = computed(() => {
	const ymax =
		store.focusVariable === 'intensity'
			? Math.max(eventStore.durationP90 || 0, 13) || eventStore.durationRange[1]
			: store.focusVariable === 'duration'
				? eventStore.sizeP90 || eventStore.sizeRange[1]
				: Math.max(
						eventStore.heatIntensityRange[1] || 0,
						eventStore.coldIntensityRange[1] || 0,
					)
	if (eventStore.selectedEvent !== null)
		return Math.max(ymax, valueForEvent.value || 0)
	return ymax
})
const ydata = computed(() => {
	return store.focusVariable === 'intensity'
		? props.eventsOfInterest.map((e) => eventStore.durationForEvent(e))
		: store.focusVariable === 'duration'
			? props.eventsOfInterest.map((e) => eventStore.sizeForEvent(e))
			: props.eventsOfInterest.map((e) => eventStore.intensityForEvent(e))
})
const ids = computed(() => {
	return props.eventsOfInterest.map((e) => e.id)
})
</script>
<template>
	<div class="multi-event-panel panel">
		<div class="scroller" ref="scrollerRef">
			<div class="chart">
				<Histogram
					:data="eventsOfInterest"
					:nbins="10"
					:xmin="xmin"
					:xmax="xmax"
					:labelFunc="(v: number) => v.toFixed(0)"
					:units="'days'"
					:highlight-value="valueForEvent"
					:types="types"
					:variable="store.focusVariable"
				/>
			</div>

			<div class="chart">
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
					:xvar="store.focusVariable"
					yvar="intensity"
				/>
			</div>
			<div class="chart">
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
					xvar="time"
					:yvar="store.focusVariable"
				/>
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

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
			padding: 0.5rem;
			border: 1px solid red;
			width: 100%;
			display: flex;
			flex-direction: row;
			gap: 0.25rem;
			justify-content: space-around;

			.histogram-root,
			.scatter-root {
				flex: 1 1 auto;
				border: 1px solid blue;
			}
		}
	}
}
</style>
