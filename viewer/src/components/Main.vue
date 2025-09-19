<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import MapComponent from './Map.vue'
import Panel from './util/Panel.vue'
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
} from '@fortawesome/free-solid-svg-icons'
import FocusFrame from './util/FocusFrame.vue'
import EventRanker from './util/EventRanker.vue'
import {
	clearFilter,
	getFilteredEvents,
	getGlobalFilteredEvents,
	onGlobalEventsReady,
	onRegionEventsReady,
} from '@/lib/eventFiltering'
import { getDayOfYear } from 'date-fns'

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

const getDayCounts = () => {
	const counts = new Map<number, Array<number>>()
	let events
	if (
		store.viewMode === 'heatmap' &&
		(store.filteringByPoint || store.filteringByRegion)
	) {
		events = getFilteredEvents()
	} else {
		events = getGlobalFilteredEvents()
	}

	events.forEach((event: ExtremeEvent) => {
		event?.times.forEach((time) => {
			const year = time.getUTCFullYear()
			const day = getDayOfYear(time)
			if (!counts.has(year)) {
				counts.set(year, Array(366).fill(0))
			}
			counts.get(year)![day - 1]++
		})
	})
	const startYear = eventStore.startYear
	const endYear = eventStore.endYear
	for (let year = startYear; year <= endYear; year++) {
		if (!counts.has(year)) {
			counts.set(year, Array(366).fill(0))
		}
	}
	return counts
}

const dayCounts = ref(getDayCounts())
watch(
	() => [store.filteringByRegion, store.filteringByPoint, store.exploreGlobal],
	() => {
		dayCounts.value = getDayCounts()
	},
)
onRegionEventsReady(() => {
	dayCounts.value = getDayCounts()
})
const globalFilteredEvents = ref([] as ExtremeEvent[])
onGlobalEventsReady(() => {
	// @ts-ignore
	console.log('Filter ready, getting global heatmap events')
	dayCounts.value = getDayCounts()
	globalFilteredEvents.value = getGlobalFilteredEvents()
})

const eventsOfInterest = ref([] as ExtremeEvent[])
onRegionEventsReady(() => {
	eventsOfInterest.value = getFilteredEvents()
})
watch(
	() => [store.filteringByRegion, store.filteringByPoint, store.exploreGlobal],
	() => {
		if (store.exploreGlobal) {
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			eventsOfInterest.value = getFilteredEvents()
		}
	},
)
</script>

<template>
	<div class="main">
		<FocusFrame
			class="focus-frame"
			:active="store.isFocused"
			@close="exitFocus"
		/>
		<MapComponent id="map"></MapComponent>
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
				:events="globalFilteredEvents"
				:day-counts="dayCounts"
				:selected-event="eventStore.selectedEvent"
				v-model="timeStore.selectedTime"
				@event-selected="eventStore.selectEvent"
				:exploring="timeStore.timePanelExpanded"
				:vertical="store.viewMode === 'heatmap'"
				:show-bars="timeStore.showBars || eventStore.eventSelected"
				:color-for-event="eventStore.colorForEvent"
			></TimeReel>
			<button
				v-if="!eventStore.eventSelected && store.viewMode !== 'heatmap'"
				class="panel-hide"
				@click="toggleTimePanelHidden"
			>
				<font-awesome-icon
					:icon="!timeStore.timePanelExpanded ? faChevronUp : faAnglesUp"
					:class="{ 'fa-rotate-180': timeStore.timePanelVisible }"
				/>
			</button>
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
					:icon="!timeStore.timePanelExpanded ? faWandMagicSparkles : faClose"
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
			id="event-panel"
			class="top"
			:active="eventStore.eventSelected && store.viewMode === 'timemachine'"
		>
			<!-- <button
				class="explore-button"
				@click="console.log('explore local events')"
			>
				<font-awesome-icon :icon="faWandMagicSparkles" />
			</button>
			<button
				class="explore-button middle"
				@click="console.log('explore local events')"
			>
				<font-awesome-icon :icon="faWandMagicSparkles" />
			</button>
			<button
				class="explore-button bottom"
				@click="console.log('explore local events')"
			>
				<font-awesome-icon :icon="faWandMagicSparkles" />
			</button> -->
			<EventGraphs
				v-if="eventStore.eventSelected"
				:selected-event="eventStore.selectedEvent"
				:time="timeStore.selectedTime"
				@date-selected="timeStore.selectedTime = $event"
			></EventGraphs>
		</Panel>
		<Panel
			id="region-panel"
			class="bottom"
			:class="{ dragging: store.draggingFilter }"
			:active="store.exploringRegion || store.exploreGlobal"
		>
			<div class="ranker" v-show="store.exploringRegion || store.exploreGlobal">
				<h1>
					<FontAwesomeIcon :icon="faClock" />
					Duration
				</h1>
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="(a, b) => b.duration - a.duration"
					:topN="100"
				/>
			</div>
			<div class="ranker" v-show="store.exploringRegion || store.exploreGlobal">
				<h1>
					<FontAwesomeIcon :icon="faExpand" />
					Size
				</h1>
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="(a, b) => b.total_area - a.total_area"
					:topN="100"
				/>
			</div>
			<div class="ranker" v-show="store.exploringRegion || store.exploreGlobal">
				<h1>
					<FontAwesomeIcon :icon="faTemperatureHigh" />
					Intensity
				</h1>
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="(a, b) => b.peak_value - a.peak_value"
					:topN="100"
				/>
			</div>
		</Panel>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

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

	.panel-toggle {
		position: absolute;
		top: -20px;
		z-index: 20;
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
		right: 1.2rem;
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

	#time-panel {
		box-shadow: rgba(0, 0, 0, 0.5) 3px 3px 3px 0px;
		width: calc(100% - 2 * $panelMargin);
		right: $panelMargin;
		bottom: $panelMargin;
		height: 40%;
		&.expanded {
			height: calc(100% - 1 * $panelMargin);
		}

		z-index: 20;

		transition: all $animTime linear;

		&.event {
			// width: calc(50% - $panelMargin);
			height: $eventTimePanelHeight;
			// padding-bottom: calc(15% - 0.75rem);
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;
		}
		.time-reel {
			border-radius: 0.5rem;
		}

		&.heatmap {
			bottom: $panelMargin;
			height: calc(100% - 4.5 * $panelMargin - 1rem);
			width: $vTimePanelWidth;
			// box-shadow: none;
			// border-bottom-left-radius: 0;

			// .time-reel {
			// 	border-bottom-left-radius: 0;
			// }

			&.focused {
				right: calc(1 * $panelMargin);
				bottom: calc(1 * $panelMargin);
				height: calc(100% - 4.5 * $panelMargin - 1rem);
			}
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
	}

	#event-frame-panel {
		left: 1.5rem;
		top: 1.5rem;
		right: 50%;
		bottom: 1.5rem;
		z-index: 10;
		background-color: transparent;
		align-items: stretch;
		border-radius: 0;
		border-top-left-radius: 6px;
		border-bottom-left-radius: 6px;
		pointer-events: none;

		.close-button {
			position: absolute;
			top: 0.5rem;
			left: 0.5rem;
			z-index: 20;
			background-color: transparent;
			border: none;
			color: $textColor;
			&:hover {
				color: $c3sred;
			}
		}

		#event-frame {
			// pointer-events: none;
			flex: 0 0 50%;
			border-top: 3rem solid $panelBg;
			border-top-left-radius: 6px;
			border-right: 3rem solid $panelBg;
			border-left: 3rem solid $panelBg;

			.decor {
				width: 100%;
				height: 100%;
				// border: 3px solid red;
				// box-shadow: rgba(0, 0, 0, 0.5) 1px 1px 3px 1px;
				box-shadow:
					inset 2px 2px 4px rgba(0, 0, 0, 0.3),
					inset -2px -2px 4px rgba(255, 255, 255, 0.1);
			}
		}
		#event-info {
			flex: 1 1 50%;
			background-color: $panelBg;
			border-radius: 0;
			border-bottom-left-radius: 6px;
			pointer-events: all;
			// padding: 0.5rem;
			// overflow-y: auto;
			// overflow-x: hidden;
			// height: calc(100% - 20px);
		}
	}

	#event-panel {
		bottom: calc($eventTimePanelHeight + $panelMargin);
		right: $panelMargin;
		left: $panelMargin;
		border-radius: 0;
		border-top-right-radius: 6px;
		border-bottom: none;
		padding-top: 1rem;
		display: flex;
		// box-shadow: rgba(0, 0, 0, 0.5) 3px 0px 3px 0px;
	}

	#region-panel {
		width: calc(100% - 2 * $panelMargin - $vTimePanelWidth);
		height: calc(40% - 2 * $panelMargin);
		bottom: calc(1 * $panelMargin);
		left: calc(1 * $panelMargin);
		// bottom: $panelMargin;;
		// right: $panelMargin;;
		display: flex;
		flex-direction: row;
		padding: calc(1 * $panelMargin);
		padding-top: calc(1.5 * $panelMargin);
		border-top-right-radius: 0;
		// border-bottom-right-radius: 0;
		border-right: 1px solid lighten($c3sred, 60%);

		&.dragging {
			opacity: 0.75;
			pointer-events: none;
		}

		gap: 1rem;
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
}
</style>
