<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import MapComponent from './Map.vue'
import Panel from './util/Panel.vue'
import Histogram from './util/Histogram.vue'
import EventTypeToggle from './util/EventTypeToggle.vue'
import TimeReel from './TimeReel.vue'
import EventGraphs from './EventGraphs.vue'
import EventInfo from './EventInfo.vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faClose,
	faBarsStaggered,
	faClock,
	faExpand,
	faTemperatureHigh,
	faCalendarDays,
} from '@fortawesome/free-solid-svg-icons'
import FocusFrame from './util/FocusFrame.vue'
import EventRanker from './util/EventRanker.vue'
import ModeToggle from './util/ModeToggle.vue'
import {
	clearFilter,
	getFilteredEvents,
	getGlobalFilteredEvents,
	onGlobalEventsReady,
	onRegionEventsReady,
	setColdOnly,
	setHotColdBoth,
	setHotOnly,
} from '@/lib/eventFiltering'
import { differenceInDays } from 'date-fns'
import MultiEventPanel from './MultiEventPanel.vue'
import {
	IconCalendar,
	IconCalendarWeek,
	IconMenu,
	IconMenu2,
	IconX,
} from '@tabler/icons-vue'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

onMounted(async () => {})
const toggleTimePanelExpanded = () => {
	timeStore.timePanelExpanded = !timeStore.timePanelExpanded
	if (timeStore.timePanelExpanded) {
		timeStore.timePanelVisible = true
	}
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

onGlobalEventsReady(() => {
	console.log('global event trigger')
})
onRegionEventsReady(() => {
	console.log('region event trigger')
})

onRegionEventsReady(() => {
	console.log(
		'eventsOfInterest updated from filtered events',
		eventsOfInterest.value,
	)
	eventsOfInterest.value = getFilteredEvents()
})
watch(
	() => eventStore.selectedEvent,
	(newVal) => {
		if (globalEventsOfInterest.value) {
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			console.log(
				'eventsOfInterest updated from filtered events',
				eventsOfInterest.value,
			)
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
			console.log(
				'eventsOfInterest updated from filtered events',
				eventsOfInterest.value,
			)
			eventsOfInterest.value = getFilteredEvents()
		}
	},
	{ immediate: true },
)

watch(
	() => [eventStore.eventTypeMode],
	() => {
		if (eventStore.eventTypeMode === 'hotcold') {
			setHotColdBoth()
		} else if (eventStore.eventTypeMode === 'cold') {
			setColdOnly()
		} else if (eventStore.eventTypeMode === 'hot') {
			setHotOnly()
		} else {
			// none selected, default to both
			setHotColdBoth()
		}
		if (globalEventsOfInterest.value) {
			globalFilteredEvents.value = getGlobalFilteredEvents()
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			console.log(
				'eventsOfInterest updated from filtered events',
				eventsOfInterest.value,
			)
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

const selectedDayIdx = computed((): number | null => {
	if (!eventStore.selectedEvent) return null
	const totalDays = eventStore.durationForEvent(eventStore.selectedEvent)
	const selectedDay = differenceInDays(
		timeStore.selectedTime,
		new Date(eventStore.selectedEvent?.times[0] || 0),
	)
	if (selectedDay < 0 || selectedDay >= totalDays) return null
	return selectedDay
})
const offset = computed(() => {
	const totalDays = eventStore.durationForEvent(eventStore.selectedEvent) + 1
	if (!selectedDayIdx.value) return 0
	return (10 * (selectedDayIdx.value + 0.5)) / totalDays
})
const funnelPoints = computed(() => {
	const totalDays = eventStore.durationForEvent(eventStore.selectedEvent) + 1
	if (selectedDayIdx.value === null || selectedDayIdx.value < 0) return ''
	const start = (90 * (selectedDayIdx.value + 0.5)) / totalDays
	const end = (90 * (selectedDayIdx.value + 1.5)) / totalDays
	return `polygon(${offset.value}% 0%,${offset.value + 90}% 0%,${end + offset.value}% 100%,${start + offset.value}% 100%)`
})

const toggleMenu = () => {
	store.hamburgerMenuOpen = !store.hamburgerMenuOpen
}
</script>

<template>
	<div class="main">
		<FocusFrame
			class="focus-frame"
			:active="store.isFocused"
			@close="exitFocus"
		/>
		<button
			id="hamburger-button"
			class="glassy color"
			:class="{ hidden: store.isFocused || timeStore.timePanelExpanded }"
			@click="toggleMenu"
		>
			<IconMenu2 size="24" aria-hidden="true" v-if="!store.hamburgerMenuOpen" />
			<IconX size="24" aria-hidden="true" v-else />
		</button>
		<Panel id="hamburger-menu" class="right" :active="store.hamburgerMenuOpen">
			<EventTypeToggle v-model="eventStore.eventTypeMode" />
			<!-- <h1>Filters</h1>
			<h1>Animation speed</h1> -->
		</Panel>

		<MapComponent id="map"></MapComponent>
		<ModeToggle
			v-model="store.viewMode"
			id="mode-toggle"
			:class="{ hidden: timeStore.timePanelExpanded }"
		/>
		<!-- Time Panel -->
		<Panel
			id="time-panel"
			:active="timeStore.timePanelVisible || eventStore.eventSelected"
			class="bottom peek"
			:class="{
				event: eventStore.eventSelected,
				expanded: timeStore.timePanelExpanded,
				[store.viewMode]: true,
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
				:eventType="eventStore.eventTypeMode"
				:value-extractor="eventStore.intensityForEvent"
			></TimeReel>
			<button
				v-if="
					timeStore.timePanelVisible &&
					!eventStore.eventSelected &&
					store.viewMode !== 'heatmap'
				"
				class="panel-expand glassy color"
				@click="toggleTimePanelExpanded"
			>
				<IconCalendarWeek
					v-if="!timeStore.timePanelExpanded"
					size="20"
					aria-hidden="true"
				/>
				<IconX v-else size="16" aria-hidden="true" />
			</button>
			<button
				v-if="
					store.viewMode === 'timemachine' &&
					!timeStore.timePanelExpanded &&
					eventStore.selectedEvent === null
				"
				:draggable="false"
				class="show-bars glassy"
				:class="{ selected: timeStore.showBars }"
				@click="timeStore.showBars = !timeStore.showBars"
			>
				<font-awesome-icon :icon="faBarsStaggered" />
			</button>
		</Panel>

		<!-- Event Info Panel -->
		<!-- This is the event information at the top center of the screen -->
		<Panel
			id="event-info-panel"
			class="top"
			:active="eventStore.selectedEvent !== null"
		>
			<EventInfo
				:selected-event="eventStore.selectedEvent"
				:event-store="eventStore"
			/>
		</Panel>

		<!-- Multi-Event Panel -->
		<!-- This is the panel on the right with rankings and histograms -->
		<MultiEventPanel
			id="multi-event-panel"
			:events-of-interest="eventsOfInterest"
			class="right"
			:active="store.showMultiEventPanel && store.viewMode !== 'timemachine'"
		/>

		<!-- Event Panel -->
		<!-- This is the panel on the left with event timeseries etc. -->
		<Panel
			id="event-panel"
			class="left"
			:class="{ small: store.viewMode === 'heatmap' }"
			:active="store.viewMode === 'timemachine' && eventStore.eventSelected"
		>
			<div class="subpanel histo" :style="`margin-left: ${offset}%`">
				<Histogram
					v-if="eventStore.selectedEvent"
					:data="
						eventStore.intensitiesForEventStep(
							eventStore.selectedEvent,
							timeStore.selectedTime,
						)
					"
					:nbins="10"
					:xmin="0"
					:xmax="eventStore.intensityRange[1]"
					:labelFunc="(v: number) => v.toFixed(1)"
					:units="'°C'"
					:types="
						eventStore
							.intensitiesForEventStep(
								eventStore.selectedEvent,
								timeStore.selectedTime,
							)
							.map(() => eventStore.selectedEvent?.event_type || 'hot')
					"
					variable="intensity"
				/>
			</div>
			<div class="funnel" :style="`clip-path: ${funnelPoints};`" />
			<div class="subpanel">
				<EventGraphs
					:selected-event="eventStore.selectedEvent"
					:event-store="eventStore"
				/>
			</div>
		</Panel>

		<!-- Event Window -->
		<!-- This is the invisible div that defines where the map should zoom to -->
		<div
			id="event-window"
			:class="{
				eventPanelOn:
					eventStore.selectedEvent !== null && store.viewMode === 'timemachine',
				multiEventPanelOn: store.showMultiEventPanel,
			}"
		/>
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

	#hamburger-button {
		position: absolute;
		top: 0.5rem;
		right: 1rem;
		border-radius: 100%;
		width: 2.5rem;
		height: 2.5rem;
		padding: 0.5rem;
		z-index: 300;
		box-shadow: var(--shadow-sm), var(--shadow-md);

		&.hidden {
			transform: translateX(150%);
		}
	}

	#hamburger-menu {
		background-color: var(--panel-bg);
		backdrop-filter: $frosty;
		top: 2 * $panelMargin;
		right: 2 * $panelMargin;
		padding: 1rem;
	}

	.focus-frame {
		overflow: hidden;
		transition: all $settleTime ease-in-out;
		z-index: 200;
		position: absolute;
	}

	.panel {
		border-radius: $borderRadius;
		background-color: var(--panel-bg);
		backdrop-filter: $frosty;
		box-shadow: var(--shadow-md);
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
		top: 0;
		left: 50%;
		z-index: 250;
		transform: translateX(-50%) translateY(-1rem);
		transition: transform $transition;
		&.hidden {
			transform: translateX(-50%) translateY(-150%);
		}
	}
	#time-panel {
		width: calc(100% - 2 * $panelMargin);
		right: $panelMargin;
		bottom: $panelMargin;
		height: 40%;
		z-index: 20;
		transition: all $transition;
		border-radius: $borderRadius;

		&.expanded {
			height: calc(100% - 2 * $panelMargin);
		}

		&.event {
			// width: calc(50% - $panelMargin);
			height: $smallTimePanelHeight;
			// padding-bottom: calc(15% - 0.75rem);
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;

			&.timemachine {
				background-color: var(--panel-bg-dark);
			}
		}

		&.heatmap {
			height: $smallTimePanelHeight;
			transition: height $transition;
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
			border-radius: $borderRadius;
		}
		.show-bars,
		.panel-expand {
			padding: 0.5rem;
			position: absolute;
			right: 0;
			top: 0;
			z-index: 20;
			width: 2.5rem;
			height: 2.5rem;
			border-radius: 0;
		}
		.show-bars {
			border-bottom-right-radius: $borderRadius;
			border-top-left-radius: $borderRadius;
		}
		.panel-expand {
			border-top-right-radius: $borderRadius;
			border-bottom-left-radius: $borderRadius;
			// background-color: var(--primary-glass);
		}
		&.expanded {
			.panel-expand {
				// right: -$panelMargin;
				// top: -$panelMargin;
				width: 2rem;
				height: 2rem;
				padding: 0.25rem;
			}
		}
		.panel-sideline {
			position: absolute;
			left: -20px;
			z-index: 20;
		}
		.show-bars {
			right: unset;
			left: 0;

			z-index: 20;
		}
	}

	#event-window {
		position: absolute;
		top: $panelMargin;
		left: $panelMargin;
		width: calc(100% - 2 * $panelMargin);
		height: calc(100% - 2 * $panelMargin - $smallTimePanelHeight);
		pointer-events: none;
		z-index: 10000;

		// background-color: rgba(0,255,0,0.1);

		&.eventPanelOn {
			left: calc($panelMargin + $eventPanelWidth);
			width: calc(100% - $eventPanelWidth - 2 * $panelMargin);
		}

		&.multiEventPanelOn {
			width: calc(100% - $multiEventPanelWidth - $panelMargin);
			&.eventPanelOn {
				width: calc(100% - $eventPanelWidth - 2 * $panelMargin);
			}
		}
	}

	#multi-event-panel {
		width: calc($multiEventPanelWidth - $panelMargin);
		height: calc(100% - 8 * $panelMargin - $smallTimePanelHeight);
		right: $panelMargin;
		bottom: calc($panelMargin + $smallTimePanelHeight);
		background-color: var(--panel-bg);
		backdrop-filter: $frosty;
		overflow: visible;

		// &.small {
		// 	transform: scale($smallMultiScale) translateX(120%);
		// 	transform-origin: bottom right;

		// 	&.active {
		// 		transform: scale($smallMultiScale);
		// 	}
		// }
	}

	#event-panel {
		width: $eventPanelWidth;
		left: $panelMargin;
		height: calc(80% - $smallTimePanelHeight - 2 * $panelMargin);
		bottom: calc(1 * $panelMargin + $smallTimePanelHeight);
		display: flex;
		flex-direction: column;
		justify-content: flex-start;
		align-items: flex-start;
		border-radius: 0;
		background-color: transparent;
		backdrop-filter: none;
		box-shadow: none;

		.subpanel {
			border-radius: $borderRadius;
			backdrop-filter: $frosty;
			box-shadow: var(--shadow-md);
			background-color: var(--panel-bg-dark);
			flex: 1 1 50%;
			width: 100%;

			&.histo {
				background-color: var(--panel-bg-dark);
				border-bottom-left-radius: $borderRadius;
				border-bottom-right-radius: $borderRadius;
				width: 90%;
				box-shadow: var(--shadow-md);
			}

			:deep(svg.graph-container) {
				border-top-left-radius: $borderRadius;
				border-top-right-radius: $borderRadius;
			}
		}

		.funnel {
			flex: 0 0 2 * $panelMargin;
			width: 100%;
			pointer-events: none;
			background-color: var(--panel-bg-dark);
			backdrop-filter: $frosty;
		}
	}

	#event-info-panel {
		// display: none;
		box-shadow: var(--shadow-md);
		background-color: var(--panel-solid);
		right: 50%;
		transform: translate(50%, 120%);
		// bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
		bottom: 0;
		height: auto;
		z-index: 250;
		transition: all $transition;
		border-bottom-left-radius: 0;
		border-bottom-right-radius: 0;
		border: 0.25rem solid var(--primary);
		border-bottom: none;

		&.active {
			transform: translate(50%, 0);
		}
	}
}
</style>
