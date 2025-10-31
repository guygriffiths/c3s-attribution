<script setup lang="ts">
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faClock,
	faExpand,
	faTemperatureHigh,
} from '@fortawesome/free-solid-svg-icons'
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
} from '@tabler/icons-vue'
import { Icon } from '@vue-leaflet/vue-leaflet/dist/src/functions'
import { ref, watch } from 'vue'
import { intervalToMs } from '@/lib/time-utils'

const store = useStore()
const eventStore = useEventStore()
const timeStore = useTimeStore()
const scrollerRef = ref<HTMLElement | null>(null)
const medalsSubRef = ref<HTMLElement | null>(null)
const scatterSubRef = ref<HTMLElement | null>(null)

defineProps<{
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

const N = 200
</script>
<template>
	<Panel class="multi-event-panel">
		<h1><IconMapStar /> {{ eventsOfInterest.length }}</h1>
		<div class="title-panel">
			<h1>
				<!-- <FontAwesomeIcon :icon="faClock" /> -->
				<IconHourglassHigh />
			</h1>
			<h1>
				<!-- <FontAwesomeIcon :icon="faExpand" /> -->
				<IconDimensions />
			</h1>
			<h1>
				<!-- <FontAwesomeIcon :icon="faTemperatureHigh" /> -->
				<IconTemperature
					v-if="eventStore.hotEventsOn && eventStore.coldEventsOn"
				/>
				<IconTemperatureSnow v-else-if="eventStore.coldEventsOn" />
				<IconTemperatureSun v-else-if="eventStore.hotEventsOn" />
				<IconTemperature v-else />
			</h1>
		</div>
		<div class="scroller" ref="scrollerRef">
			<div class="medals-subpanel subpanel" ref="medalsSubRef">
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="
						(a, b) =>
							eventStore.durationForEvent(b) - eventStore.durationForEvent(a)
					"
					:topN="200"
				/>
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="
						(a, b) => eventStore.sizeForEvent(b) - eventStore.sizeForEvent(a)
					"
					:topN="200"
				/>

				<EventRanker
					:events="eventsOfInterest"
					:sort-func="
						(a, b) =>
							eventStore.intensityForEvent(b) - eventStore.intensityForEvent(a)
					"
					:topN="200"
				/>
			</div>
			<div class="histogram-subpanel subpanel">
				<Histogram
					:data="eventsOfInterest.map((e) => eventStore.durationForEvent(e))"
					:nbins="10"
					:xmin="eventStore.durationRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.durationRange[1],
									eventStore.durationForEvent(eventStore.selectedEvent),
								)
							: eventStore.durationRange[1]
					"
					:labelFunc="(v: number) => v.toFixed(0)"
					:units="'days'"
					:highlight-value="
						eventStore.selectedEvent
							? eventStore.durationForEvent(eventStore.selectedEvent)
							: null
					"
					:types="eventsOfInterest.map((e) => e.event_type)"
					variable="duration"
				/>
				<Histogram
					:data="eventsOfInterest.map((e) => eventStore.sizeForEvent(e))"
					:nbins="10"
					:xmin="eventStore.sizeRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.sizeRange[1],
									eventStore.sizeForEvent(eventStore.selectedEvent),
								)
							: eventStore.sizeRange[1]
					"
					:labelFunc="(v: number) => (v / 1000).toFixed(1) + 'k'"
					:units="'m²'"
					:highlight-value="
						eventStore.selectedEvent
							? eventStore.sizeForEvent(eventStore.selectedEvent)
							: null
					"
					:types="eventsOfInterest.map((e) => e.event_type)"
					variable="size"
				/>
				<Histogram
					:data="eventsOfInterest.map((e) => eventStore.intensityForEvent(e))"
					:nbins="10"
					:xmin="eventStore.intensityRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.intensityRange[1],
									eventStore.intensityForEvent(eventStore.selectedEvent),
								)
							: eventStore.intensityRange[1]
					"
					:labelFunc="(v: number) => v.toFixed(0)"
					:units="'°C'"
					:highlight-value="
						eventStore.selectedEvent
							? eventStore.intensityForEvent(eventStore.selectedEvent)
							: null
					"
					:types="eventsOfInterest.map((e) => e.event_type)"
					variable="intensity"
				/>
			</div>
			<div class="scatter-subpanel subpanel" ref="scatterSubRef">
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => eventStore.durationForEvent(e))"
					:ydata="eventsOfInterest.map((e) => eventStore.intensityForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="eventStore.durationRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.durationRange[1],
									eventStore.durationForEvent(eventStore.selectedEvent),
								)
							: eventStore.durationRange[1]
					"
					:ymin="eventStore.intensityRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.intensityRange[1],
									eventStore.intensityForEvent(eventStore.selectedEvent),
								)
							: eventStore.intensityRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="duration"
					yvar="intensity"
				/>
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => eventStore.sizeForEvent(e))"
					:ydata="eventsOfInterest.map((e) => eventStore.durationForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="eventStore.sizeRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.sizeRange[1],
									eventStore.sizeForEvent(eventStore.selectedEvent),
								)
							: eventStore.sizeRange[1]
					"
					:ymin="eventStore.durationRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.durationRange[1],
									eventStore.durationForEvent(eventStore.selectedEvent),
								)
							: eventStore.durationRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="size"
					yvar="duration"
				/>
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => eventStore.intensityForEvent(e))"
					:ydata="eventsOfInterest.map((e) => eventStore.sizeForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="eventStore.intensityRange[0]"
					:xmax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.intensityRange[1],
									eventStore.intensityForEvent(eventStore.selectedEvent),
								)
							: eventStore.intensityRange[1]
					"
					:ymin="eventStore.sizeRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.sizeRange[1],
									eventStore.sizeForEvent(eventStore.selectedEvent),
								)
							: eventStore.sizeRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="intensity"
					yvar="size"
				/>
			</div>
			<div class="ts-subpanel subpanel">
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => e.times[0].getTime())"
					:ydata="eventsOfInterest.map((e) => eventStore.durationForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="timeStore.startTime.getTime()"
					:xmax="timeStore.endTime.getTime()"
					:ymin="eventStore.durationRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.durationRange[1],
									eventStore.durationForEvent(eventStore.selectedEvent),
								)
							: eventStore.durationRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="time"
					yvar="duration"
				/>
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => e.times[0].getTime())"
					:ydata="eventsOfInterest.map((e) => eventStore.sizeForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="timeStore.startTime.getTime()"
					:xmax="timeStore.endTime.getTime()"
					:ymin="eventStore.sizeRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.sizeRange[1],
									eventStore.sizeForEvent(eventStore.selectedEvent),
								)
							: eventStore.sizeRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="time"
					yvar="size"
				/>
				<ScatterPlot
					:xdata="eventsOfInterest.map((e) => e.times[0].getTime())"
					:ydata="eventsOfInterest.map((e) => eventStore.intensityForEvent(e))"
					:types="eventsOfInterest.map((e) => e.event_type)"
					:xmin="timeStore.startTime.getTime()"
					:xmax="timeStore.endTime.getTime()"
					:ymin="eventStore.intensityRange[0]"
					:ymax="
						eventStore.selectedEvent
							? Math.max(
									eventStore.intensityRange[1],
									eventStore.intensityForEvent(eventStore.selectedEvent),
								)
							: eventStore.intensityRange[1]
					"
					:ids="eventsOfInterest.map((e) => e.id)"
					:highlightId="eventStore.selectedEventId"
					xvar="time"
					yvar="intensity"
				/>
			</div>
		</div>
		<button
			class="analytics-button glassy selected"
			@click="store.showAnalytics = !store.showAnalytics"
		>
			<span v-if="store.showAnalytics">
				<IconAward />
				<IconArrowUp />
			</span>
			<span v-else>
				<IconChartScatter />
				<IconArrowDown />
			</span>
		</button>
	</Panel>
</template>
<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.multi-event-panel {
	display: flex;
	flex-direction: column;
	padding: 0 0.125rem;

	.spacer {
		flex: 0 0 1rem;
		position: relative;

		.floating-label {
			position: absolute;
			width: 3rem;
			min-height: 3rem;
			top: 1rem;
			left: 0;
			background-color: var(--panel-bg);
			backdrop-filter: $frosty;
			padding: 0.1rem 0.5rem;
			border-radius: 100%;
			display: flex;
			flex-direction: column;
			align-items: center;
			font-size: 0.8rem;
			color: var(--text-secondary);
			z-index: 1000000;
		}
	}
	.title-panel {
		flex: 1 1 auto;
		display: flex;
		justify-content: space-around;
		width: 100%;
		border-top: 0.5px solid var(--border);
	}
	h1 {
		// position: absolute;
		// top: -1.75rem;
		// left: 0;
		margin: 0;
		padding: 0;
		margin: 0;
		background-color: transparent;
		font-size: 0.9rem;
		text-align: center;
		z-index: 10;
		display: flex;
		gap: 0.25rem;
		
	}

	.scroller {
		height: 100%;
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		overflow-y: hidden;
		overflow-x: visible;
		gap: 0.25rem;
		justify-content: space-between;

		.label {
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: center;
			width: 100%;
			height: 2rem;
			flex: 0 0 2rem;
			font-size: 1rem;
			color: var(--text-primary);
		}

		.subpanel {
			flex: 0 0 calc(33.33333% - 0.5rem);
			width: 100%;
			display: flex;
			flex-direction: row;
			gap: 0.25rem;
			justify-content: space-around;
			// border: 0.5px solid var(--primary);

			.event-ranker-root,
			.histogram-root,
			.scatter-root {
				background-color: var(--panel-alt);
				backdrop-filter: $frosty;
				// margin: 0 0.25rem;
			}
			// padding: 0.25rem;

			&.medals-subpanel {
				height: calc(66.66666% - 1rem);
			}
		}
	}

	.analytics-button {
		width: 100%;
		height: 2rem;
		display: flex;
		justify-content: center;
		padding: 0;
		margin-top: 2px;
		background-color: var(--primary-glass) !important;
		backdrop-filter: none !important;

		svg {
			height: 2rem;
			margin: 0;
		}
	}

	.medals-subpanel {
		.event-ranker-root {
			flex: 1 1 33%;
			height: 100%;
		}
	}

	.histogram-subpanel {
	}

	.scatter-subpanel {
	}
}
</style>
