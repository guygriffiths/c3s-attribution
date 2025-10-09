<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import MapComponent from './Map.vue'
import Panel from './util/Panel.vue'
import Histogram from './util/Histogram.vue'
import ScatterPlot from './util/ScatterPlot.vue'
import TimeReel from './TimeReel.vue'
import EventGraphs from './EventGraphs.vue'
import EventInfo from './EventInfo.vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faChevronUp,
	faAnglesUp,
	faWandMagicSparkles,
	faClose,
	faBarsStaggered,
	faClock,
	faExpand,
	faTemperatureHigh,
	faRankingStar,
	faCalendarDays,
} from '@fortawesome/free-solid-svg-icons'
import FocusFrame from './util/FocusFrame.vue'
import EventRanker from './util/EventRanker.vue'
import ModeToggle from './util/ModeToggle.vue'
import {
	clearFilter,
	getFilteredEvents,
	getFilteredIds,
	getGlobalFilteredEvents,
	onGlobalEventsReady,
	onRegionEventsReady,
	setColdOnly,
	setHotColdBoth,
	setHotOnly,
} from '@/lib/eventFiltering'
import { differenceInDays } from 'date-fns'
import { glob } from 'fs'
import { difference } from 'd3'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

onMounted(async () => {})
const toggleLabel = computed(() =>
	timeStore.timePanelVisible ? $l.value.hideTimePanel : $l.value.showTimePanel,
)
const toggleTimePanelExpanded = () => {
	timeStore.timePanelExpanded = !timeStore.timePanelExpanded
	if (timeStore.timePanelExpanded) {
		timeStore.timePanelVisible = true
	}
}
const toggleTimePanelHidden = () => {
	timeStore.timePanelVisible = !timeStore.timePanelVisible
	// if (!timeStore.timePanelVisible) {
	// 	timeStore.timePanelExpanded = false
	// }
}

const exitFocus = () => {
	eventStore.selectEvent(null)
	clearFilter()
	store.draggingFilter = false
}

const globalEventsOfInterest = computed((): boolean => {
	return (
		store.viewMode === 'timemachine' ||
		store.exploreGlobal ||
		(!(store.filteringByRegion && store.regionFilterReady) &&
			!store.filteringByPoint)
	)
})

const globalFilteredEvents = ref([] as ExtremeEvent[])
const eventsOfInterest = ref([] as ExtremeEvent[])
onGlobalEventsReady(() => {
	globalFilteredEvents.value = getGlobalFilteredEvents()
	if (globalEventsOfInterest.value) {
		eventsOfInterest.value = globalFilteredEvents.value
	}
})

onRegionEventsReady(() => {
	eventsOfInterest.value = getFilteredEvents()
})
watch(
	() => eventStore.selectedEvent,
	(newVal) => {
		if (globalEventsOfInterest.value) {
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			eventsOfInterest.value = getFilteredEvents()
		}
	},
)
watch(
	() => [
		store.filteringByRegion,
		store.regionFilterReady,
		store.filteringByPoint,
		store.exploreGlobal,
		store.viewMode,
	],
	() => {
		if (globalEventsOfInterest.value) {
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			eventsOfInterest.value = getFilteredEvents()
		}
	},
	{ immediate: true },
)

watch(
	() => [eventStore.coldEventsOn, eventStore.hotEventsOn],
	() => {
		if (eventStore.coldEventsOn && eventStore.hotEventsOn) {
			setHotColdBoth()
		} else if (eventStore.coldEventsOn) {
			setColdOnly()
		} else if (eventStore.hotEventsOn) {
			setHotOnly()
		} else {
			// none selected, default to both
			setHotColdBoth()
		}
		if (globalEventsOfInterest.value) {
			globalFilteredEvents.value = getGlobalFilteredEvents()
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			eventsOfInterest.value = getFilteredEvents()
		}
	},
	{ immediate: true },
)

const mode = computed((): TimeReelMode => {
	if (store.viewMode === 'heatmap') return 'timeline'
	if (eventStore.eventSelected) return 'eventzoom'
	if (timeStore.timePanelExpanded) return 'overview'
	return 'default'
})
</script>

<template>
	<div class="main">
		<FocusFrame
			class="focus-frame"
			:active="store.isFocused"
			@close="exitFocus"
		/>
		<MapComponent id="map"></MapComponent>
		<ModeToggle v-model="store.viewMode" id="mode-toggle" />
		<Panel
			id="time-panel"
			:active="timeStore.timePanelVisible || eventStore.eventSelected"
			class="bottom peek"
			:class="{
				event: eventStore.eventSelected,
				expanded: timeStore.timePanelExpanded,
				heatmap: store.viewMode === 'heatmap',
				focused: store.isFocused,
			}"
		>
			<TimeReel
				id="times"
				:start="timeStore.startTime"
				:end="timeStore.endTime"
				:events="eventsOfInterest"
				:dragging-filter="store.draggingFilter"
				:selected-event="eventStore.selectedEvent"
				v-model="timeStore.selectedTime"
				@event-selected="eventStore.selectEvent"
				:mode="mode"
				:show-bars="timeStore.showBars"
				:color-for-event="eventStore.colorForEvent"
				:class="mode"
				:hot="eventStore.hotEventsOn"
				:cold="eventStore.coldEventsOn"
				:value-extractor="eventStore.intensityForEvent"
			></TimeReel>
			<!-- <button
				v-if="!eventStore.eventSelected && store.viewMode !== 'heatmap'"
				class="panel-hide"
				@click="toggleTimePanelHidden"
			>
				<font-awesome-icon
					:icon="!timeStore.timePanelExpanded ? faChevronUp : faAnglesUp"
					:class="{ 'fa-rotate-180': timeStore.timePanelVisible }"
				/>
			</button> -->
			<button
				v-if="
					timeStore.timePanelVisible &&
					!eventStore.eventSelected &&
					store.viewMode !== 'heatmap'
				"
				class="panel-expand"
				@click="toggleTimePanelExpanded"
			>
				<font-awesome-icon
					:icon="!timeStore.timePanelExpanded ? faCalendarDays : faClose"
				/>
			</button>
			<button
				v-if="store.viewMode === 'timemachine' && !timeStore.timePanelExpanded"
				:draggable="false"
				class="show-bars"
				:class="{ active: timeStore.showBars }"
				@click="timeStore.showBars = !timeStore.showBars"
			>
				<font-awesome-icon :icon="faBarsStaggered" />
			</button>
		</Panel>

		<Panel
			id="multi-event-panel"
			class="right"
			:class="{ small: store.viewMode === 'timemachine' }"
			:active="
				store.showMultiEventPanel &&
				(store.viewMode !== 'timemachine' || eventStore.eventSelected)
			"
		>
			<button
				class="panel-toggle"
				@click="store.showMultiEventPanel = !store.showMultiEventPanel"
			>
				<font-awesome-icon
					:icon="!store.showMultiEventPanel ? faRankingStar : faClose"
				/>
			</button>
			<div class="title-panel">
				<h1>
					<FontAwesomeIcon :icon="faClock" />
					Duration
				</h1>
				<h1>
					<FontAwesomeIcon :icon="faExpand" />
					Size
				</h1>
				<h1>
					<FontAwesomeIcon :icon="faTemperatureHigh" />
					Intensity
				</h1>
			</div>
			<div class="medals-subpanel subpanel">
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
				/>
			</div>
			<div class="scatter-subpanel subpanel">
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
				/>
			</div>
		</Panel>

		<div id="multi-event-window" />
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

$smallTimePanelHeight: max(6rem, 10%);

.main {
	display: flex;
	flex-direction: column;
	overflow: hidden;
	height: 100vh;
	width: 100vw;
	max-width: 100vw;
	max-height: 100vh;
	position: relative;

	.focus-frame {
		overflow: hidden;
		transition: all $settleTime ease-in-out;
		z-index: 200;
	}

	#buttons-debug {
		position: absolute;
		left: -10px;
		bottom: -10px;
	}

	#map {
		flex: 1 1 100%;
		z-index: 0;
	}
	#mode-toggle {
		position: absolute;
		bottom: 0;
		left: 50%;
		z-index: 250;
		transform: translateX(-50%);
		// border-bottom-right-radius: 0;
		// border-bottom-left-radius: 0;
		// padding: 0 3rem;
	}
	#time-panel {
		box-shadow: rgba(0, 0, 0, 0.5) 3px 3px 3px 0px;
		width: calc(100% - 2 * $panelMargin);
		right: $panelMargin;
		bottom: $panelMargin;
		height: 40%;
		z-index: 20;
		transition: all $animTime ease-in-out;

		&.expanded {
			height: calc(100% - 4 * $panelMargin);
		}

		&.event {
			// width: calc(50% - $panelMargin);
			height: $smallTimePanelHeight;
			// padding-bottom: calc(15% - 0.75rem);
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;
		}

		transition: height 0 linear;
		&.heatmap {
			height: $smallTimePanelHeight;
			transition: height $animTime linear;
		}

		#times {
			width: 100%;
			height: 100%;
			overflow-x: auto;
			overflow-y: hidden;
			display: flex;
			align-items: center;
			justify-content: center;
			border: none;
		}
		.show-bars,
		.panel-expand,
		.panel-hide {
			padding: 0.5rem;
			position: absolute;
			right: 0;
			top: -0.5rem;
			z-index: 20;
			border: none;
			background-color: transparent;
			color: $textColor;
			&:hover {
				color: $c3sred;
			}
		}
		.panel-expand {
			// right: 1.2rem;
		}
		.panel-sideline {
			position: absolute;
			left: -20px;
			z-index: 20;
		}
		.show-bars {
			right: unset;
			left: 0;

			top: -0.5rem;
			z-index: 20;

			&.active {
				color: $c3sred;
				filter: drop-shadow(0 0 2px rgb(255, 255, 255))
					drop-shadow(0 0 5px rgb(255, 255, 255));
			}
		}
	}

	#multi-event-window {
		position: absolute;
		top: 0;
		left: 0;
		width: 60%;
		height: 100%; //calc(100% - $panelMargin - $smallTimePanelHeight);
		pointer-events: none;
		background-color: rgba(34, 150, 200, 0);
	}

	#multi-event-panel {
		display: flex;
		flex-direction: column;
		// gap: 0.5rem;
		width: calc(40% - $panelMargin);
		height: calc(100% - 3 * $panelMargin - $smallTimePanelHeight);
		right: $panelMargin;
		bottom: calc(1 * $panelMargin + $smallTimePanelHeight);

		&.small {
			transform: scale(0.6) translateX(120%);
			transform-origin: bottom right;

			&.active {
				transform: scale(0.6);
			}
		}

		.panel-toggle {
			position: absolute;
			top: 50%;
			left: -2.5rem;
			padding: 1rem;
			border: none;
			border-top-right-radius: 0;
			border-bottom-right-radius: 0;
			border-top-left-radius: 100%;
			border-bottom-left-radius: 100%;
			// padding-left: 1rem;
			// background-color: transparent;
			color: $textColor;
			z-index: -100;
			&:hover {
				color: $c3sred;
			}

			svg {
				margin-left: -0.5rem;
			}
		}

		.title-panel {
			display: flex;
			justify-content: space-around;
			justify-content: space-between;
			width: 100%;
			h1 {
				// position: absolute;
				// top: -1.75rem;
				// left: 0;
				flex: 1 1 100%;
				margin: 0;
				padding: 0.5rem 0;
				background-color: transparent;
				font-size: 0.9rem;
				text-align: center;
				z-index: 10;
			}
		}

		.subpanel {
			flex: 1 1 100%;
			height: 33%;
			width: 100%;
			display: flex;
			flex-direction: row;
			// gap: 0.5rem;
			border: 0.5px solid $c3sred;
			// margin-bottom: 0.5rem;
		}

		.medals-subpanel {
			.event-ranker {
				flex: 1 1 33%;
				height: 100%;
			}
		}

		.histogram-subpanel {
		}

		.scatter-subpanel {
		}
	}

	#event-rankings-panel {
		// z-index: 500;
		width: calc(40% - $panelMargin);
		height: calc(30% - 2 * $panelMargin);

		bottom: calc(
			1 * $panelMargin + $smallTimePanelHeight + 30% + 30% - 1 * $panelMargin
		);
		right: calc(1 * $panelMargin);
		gap: 0.5rem;
		display: flex;
		flex-direction: row;
		padding: calc(0.5 * $panelMargin);
		padding-top: calc(1.25 * $panelMargin);
		border-top-right-radius: 0;

		&.dragging {
			opacity: 0.75;
			pointer-events: none;
		}

		.ranker {
			flex: 1 1 33%;
			// margin-right: 1rem;
			// box-shadow: rgba(0, 0, 0, 0.2) 0px 4px 6px -1px,
			// 	rgba(0, 0, 0, 0.1) 0px 2px 4px -1px;
			// border: 1px solid rgba(0, 0, 0, 0.1);
			// border: 1px solid rgba(255, 255, 255, 0.1);
			// backdrop-filter: blur(5px);
			height: 100%;
			min-width: 0; // allow flexbox to shrink it
			padding: 0;
			border: 1px solid $c3sred;
			position: relative;

			.event-ranker {
				height: 100%;
				width: 100%;
			}

			h1 {
				position: absolute;
				top: -1.75rem;
				left: 0;
				margin: 0;
				padding: 0.5rem 0;
				background-color: transparent;
				font-size: 0.9rem;
				text-align: center;
				z-index: 10;
			}
		}
	}

	#event-ts-panel {
		// z-index: 500;
		width: calc(40% - 2 * $panelMargin);
		height: calc(20% - 2 * $panelMargin);
		bottom: calc(1 * $panelMargin + $smallTimePanelHeight + 40%);
		right: calc(1 * $panelMargin);
		gap: 0;
		display: flex;
		flex-direction: column;
		padding: calc(0.5 * $panelMargin);
		// padding-top: calc(1.25 * $panelMargin);
		// padding-bottom: 2px;

		.scatter-root {
			flex: 1 1 33%;
			height: 33%;
			// box-shadow:
			// 	rgba(0, 0, 0, 0.5) 0px 4px 6px -1px,
			// 	rgba(0, 0, 0, 0.25) 0px 2px 4px -1px;
		}
	}

	#event-histograms-panel {
		// z-index: 500;
		width: calc(40% - $panelMargin);
		height: calc(20% - 2 * $panelMargin);
		bottom: calc(1 * $panelMargin + $smallTimePanelHeight + 20%);
		right: calc(1 * $panelMargin);
		gap: 0.5rem;
		display: flex;
		flex-direction: row;
		padding: calc(0.5 * $panelMargin);
		// padding-top: calc(1.25 * $panelMargin);
		// padding-bottom: 2px;

		.histogram-root {
			box-shadow:
				rgba(0, 0, 0, 0.5) 0px 4px 6px -1px,
				rgba(0, 0, 0, 0.25) 0px 2px 4px -1px;
		}
	}

	#event-scatter-panel {
		// z-index: 500;
		width: calc(40% - $panelMargin);
		height: calc(20% - 2 * $panelMargin);
		bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
		right: calc(1 * $panelMargin);
		gap: 0.5rem;
		display: flex;
		flex-direction: row;
		padding: calc(0.5 * $panelMargin);
		// padding-top: calc(1.25 * $panelMargin);
		// padding-bottom: 2px;
		.scatter-root {
			box-shadow:
				rgba(0, 0, 0, 0.5) 0px 4px 6px -1px,
				rgba(0, 0, 0, 0.25) 0px 2px 4px -1px;
		}
	}
}
</style>
