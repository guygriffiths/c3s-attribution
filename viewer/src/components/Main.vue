<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import MapComponent from './Map.vue'
import EventTypeToggle from './util/EventTypeToggle.vue'
import TimeReel from './TimeReel.vue'
import EventGraphs from './EventGraphs.vue'
import EventInfoPanel from './EventInfoPanel.vue'
import SelectedEventInfoPanel from './SelectedEventInfoPanel.vue'
import FilterPanel from './FilterPanel.vue'
import FocusFrame from './util/FocusFrame.vue'
import ModeToggle from './util/ModeToggle.vue'
import {
	getCurrentEvents,
	getFilteredEvents,
	getGlobalFilteredEvents,
	onCurrentEventsReady,
	onGlobalEventsReady,
	onRegionEventsReady,
	setColdOnly,
	setHotOnly,
	setHotColdBoth,
	getTimeRangedEvents,
} from '@/lib/eventsDB'
import { differenceInDays } from 'date-fns'
import MultiEventSmartPanel from './MultiEventSmartPanel.vue'
import {
	IconCalendarWeek,
	IconChartBar,
	IconChartHistogram,
	IconInfoSquareRounded,
	IconMenu2,
	IconWindowMaximize,
	IconWindowMinimize,
	IconX,
} from '@tabler/icons-vue'
import EventDayPanel from './EventDayPanel.vue'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

onMounted(async () => {})
const toggleTimePanelExpanded = () => {
	timeStore.timePanelExpanded = !timeStore.timePanelExpanded
}

const exitFocus = () => {
	eventStore.selectEvent(null)
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
		// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
		eventsOfInterest.value = globalFilteredEvents.value
	}
})
const currentEvents = ref([] as ExtremeEvent[])
onCurrentEventsReady(() => {
	currentEvents.value = getCurrentEvents(timeStore.selectedTime)
})
watch(
	() => timeStore.selectedTime,
	(newVal) => {
		currentEvents.value = getCurrentEvents(newVal)
	},
)
const timeRangeEvents = ref([] as ExtremeEvent[])
let pending = false
watch(
	() => [store.viewMode, timeStore.startTimeFilter, timeStore.endTimeFilter],
	() => {
		if (pending) return
		pending = true
		requestAnimationFrame(() => {
			pending = false
			if (
				store.filteringByPoint ||
				(store.filteringByRegion && store.regionFilterReady)
			) {
				eventsOfInterest.value = getFilteredEvents()
				timeRangeEvents.value = eventsOfInterest.value.filter(
					(e) =>
						e.times[0] <= timeStore.endTimeFilter.getTime() &&
						e.times[e.times.length - 1] >= timeStore.startTimeFilter.getTime(),
				)
			} else {
				const newEvents = getTimeRangedEvents(
					timeStore.startTimeFilter,
					timeStore.endTimeFilter,
				)
				if (eventStore.selectedEvent) {
					// Ensure selected event is included
					if (!newEvents.find((e) => e.id === eventStore.selectedEvent?.id)) {
						// @ts-ignore
						newEvents.push(eventStore.selectedEvent)
					}
				}

				timeRangeEvents.value = newEvents
			}
		})
	},
	{ immediate: true },
)

onRegionEventsReady(() => {
	eventsOfInterest.value = getFilteredEvents()
	timeRangeEvents.value = eventsOfInterest.value.filter(
		(e) =>
			e.times[0] <= timeStore.endTimeFilter.getTime() &&
			e.times[e.times.length - 1] >= timeStore.startTimeFilter.getTime(),
	)
})

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
			// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
			eventsOfInterest.value = globalFilteredEvents.value
			timeRangeEvents.value = getTimeRangedEvents(
				timeStore.startTimeFilter,
				timeStore.endTimeFilter,
			)
		} else {
			// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
			eventsOfInterest.value = getFilteredEvents()
		}
	},
	{ immediate: true },
)

watch(
	() => [eventStore.eventTypeMode],
	() => {
		if (eventStore.eventTypeMode === 'cold') {
			setColdOnly()
		} else if (eventStore.eventTypeMode === 'hot') {
			setHotOnly()
		} else {
			setHotColdBoth()
		}
		if (globalEventsOfInterest.value) {
			globalFilteredEvents.value = getGlobalFilteredEvents()
			// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
			eventsOfInterest.value = globalFilteredEvents.value
		} else {
			// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
			eventsOfInterest.value = getFilteredEvents()
		}
		currentEvents.value = getCurrentEvents(timeStore.selectedTime)
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
	if (
		!eventStore.selectedEvent ||
		!eventStore.selectedEvent.hasOwnProperty('pixel_max_values')
	)
		return null
	const totalDays = eventStore.durationForEvent(eventStore.selectedEvent)
	const selectedDay = differenceInDays(
		timeStore.selectedTime,
		new Date(eventStore.selectedEvent?.times[0] || 0),
	)
	if (selectedDay < 0 || selectedDay >= totalDays) return null
	return selectedDay
})
</script>

<template>
	<div class="main">
		<FocusFrame id="focus-frame" :active="store.isFocused" @close="exitFocus" />

		<MapComponent id="map"></MapComponent>

		<div
			id="logo"
			:class="{ 'disable-pointer-events': store.isFocused }"
			:aria-label="
				eventStore.eventTypeMode === 'hot'
					? $l.hotTitle
					: eventStore.eventTypeMode === 'cold'
						? $l.coldTitle
						: $l.hotcoldTitle
			"
		>
			<img src="@/assets/img/c3s-logo.png" alt="C3S Logo" aria-hidden="true" />
			<h1 aria-hidden="true">
				Extreme
				<span
					class="eventtype"
					@click="eventStore.cycleEventType()"
					role="button"
					tabindex="-1"
				>
					{{
						eventStore.eventTypeMode === 'hot'
							? 'Heat Event'
							: eventStore.eventTypeMode === 'cold'
								? 'Cold Event'
								: 'Event'
					}}
				</span>
				Explorer
			</h1>
		</div>

		<ModeToggle
			v-model="store.viewMode"
			id="mode-toggle"
			:class="{ hidden: timeStore.timePanelExpanded }"
		/>

		<button
			id="hamburger-button"
			class="glassy color"
			:class="{
				hidden: store.isFocused || timeStore.timePanelExpanded,
				close: store.hamburgerMenuOpen,
			}"
			:inert="store.isFocused || timeStore.timePanelExpanded ? 'true' : undefined"
			@click="store.hamburgerMenuOpen = !store.hamburgerMenuOpen"
			v-tooltip="store.hamburgerMenuOpen ? $l.close : $l.hamburger"
		>
			<IconMenu2 size="24" aria-hidden="true" v-if="!store.hamburgerMenuOpen" />
			<IconX size="24" aria-hidden="true" v-else />
		</button>
		<div
			id="hamburger-menu"
			class="panel top"
			:class="{ active: store.hamburgerMenuOpen }"
			:inert="!store.hamburgerMenuOpen ? 'true' : undefined"
		>
			<EventTypeToggle
				:model-value="eventStore.eventTypeMode"
				@update:model-value="eventStore.setEventTypeMode"
			/>
			<FilterPanel v-model="eventStore.filters" />
			<!-- <h1>Filters</h1>
			<h1>Animation speed</h1> -->
		</div>

		<!-- Event Panel -->
		<!-- This is the panel on the left with graphs for an individual event -->
		<EventDayPanel
			id="event-day-panel"
			:selected-event="eventStore.selectedEvent"
			:selected-index="selectedDayIdx !== null ? selectedDayIdx : 0"
			class="panel left chart"
			:class="{
				active: store.viewMode === 'timemachine' && eventStore.eventSelected,
			}"
			:inert="
				store.viewMode !== 'timemachine' || !eventStore.eventSelected
					? 'true'
					: undefined
			"
		/>
		<EventGraphs
			id="event-graphs"
			:selected-event="eventStore.selectedEvent"
			:event-store="eventStore"
			class="panel left chart"
			:class="{
				active: store.viewMode === 'timemachine' && eventStore.eventSelected,
			}"
			:inert="
				store.viewMode !== 'timemachine' || !eventStore.eventSelected
					? 'true'
					: undefined
			"
			@dateSelected="
				(date: number) => {
					timeStore.selectedTime = new Date(date)
				}
			"
		/>

		<!-- Multi-Event Panel -->
		<!-- This is the panel on the right with rankings and histograms -->
		<button
			id="multi-button"
			class="glassy color"
			:class="{
				hidden: store.viewMode !== 'heatmap' || store.maximizeMultiPanel,
				close: store.showMultiPanel,
			}"
			:inert="
				store.viewMode !== 'heatmap' || store.maximizeMultiPanel
					? 'true'
					: undefined
			"
			@click="store.showMultiPanel = !store.showMultiPanel"
			v-tooltip="store.showMultiPanel ? $l.close : $l.multiEventPanel"
		>
			<IconChartHistogram
				size="24"
				aria-hidden="true"
				v-if="!store.showMultiPanel"
			/>
			<IconX size="24" aria-hidden="true" v-else />
		</button>

		<MultiEventSmartPanel
			id="multi-event-panel"
			:events-of-interest="
				store.viewMode === 'timemachine' ? currentEvents : timeRangeEvents
			"
			:background-events="
				store.filteringByPoint || store.filteringByRegion
					? globalFilteredEvents
					: []
			"
			:selectedEvent="eventStore.selectedEvent"
			class="right panel"
			:class="{
				selected: eventStore.eventSelected,
				active: store.showMultiPanel && store.viewMode === 'heatmap',
				maximize: store.maximizeMultiPanel,
			}"
			:inert="
				!store.showMultiPanel || store.viewMode !== 'heatmap' ? 'true' : undefined
			"
			><button
				id="multimax-button"
				class="glassy color"
				:class="{
					hidden: store.viewMode !== 'heatmap',
					close: store.showMultiPanel,
				}"
				:inert="store.viewMode !== 'heatmap' ? 'true' : undefined"
				@click="store.maximizeMultiPanel = !store.maximizeMultiPanel"
				v-tooltip="
					store.maximizeMultiPanel
						? $l.restoreMultiEventPanel
						: $l.maximiseMultiEventPanel
				"
			>
				<IconWindowMaximize
					size="24"
					aria-hidden="true"
					v-if="!store.maximizeMultiPanel"
					style="transform: scaleX(-1)"
				/>
				<IconWindowMinimize
					size="24"
					aria-hidden="true"
					style="transform: scaleX(-1)"
					v-else
				/>
			</button>
		</MultiEventSmartPanel>

		<!-- Event Info Panel -->
		<button
			id="info-button"
			class="glassy color"
			:class="{
				hidden:
					timeStore.timePanelExpanded ||
					(store.isFocused && store.viewMode === 'timemachine') ||
					store.maximizeMultiPanel,
				close: store.showInfoPanel,
			}"
			:inert="
				timeStore.timePanelExpanded ||
				(store.isFocused && store.viewMode === 'timemachine') ||
				store.maximizeMultiPanel
					? 'true'
					: undefined"
			@click="store.showInfoPanel = !store.showInfoPanel"
			v-tooltip="store.showInfoPanel ? $l.close : $l.showInfoPanel"
		>
			<IconInfoSquareRounded
				size="24"
				aria-hidden="true"
				v-if="!store.showInfoPanel"
			/>
			<IconX size="24" aria-hidden="true" v-else />
		</button>
		<EventInfoPanel
			id="event-info-panel"
			:selected-event="eventStore.selectedEvent"
			:main-store="store"
			:event-store="eventStore"
			:time-store="timeStore"
			:events-of-interest="
				store.viewMode === 'timemachine' ? currentEvents : timeRangeEvents
			"
			:class="{
				'disable-transitions': timeStore.isPlaying,
				show:
					store.showInfoPanel &&
					!timeStore.timePanelExpanded &&
					!(store.isFocused && store.viewMode === 'timemachine') &&
					store.maximizeMultiPanel === false,
			}"
			:inert="
				!store.showInfoPanel ||
				timeStore.timePanelExpanded ||
				(store.isFocused && store.viewMode === 'timemachine') ||
				store.maximizeMultiPanel
					? 'true'
					: undefined"
		>
		</EventInfoPanel>
		<SelectedEventInfoPanel
			id="selected-event-info-panel"
			class="chart"
			v-if="eventStore.selectedEvent"
			:selected-event="eventStore.selectedEvent"
			:event-store="eventStore"
			:class="{
				show: eventStore.selectedEvent !== null && store.showInfoPanel,
				single: store.viewMode === 'timemachine' && store.isFocused,
			}"
			:inert="
				eventStore.selectedEvent === null || !store.showInfoPanel ? 'true' : undefined"
		/>

		<!-- Time Panel -->
		<div
			id="time-panel"
			class="panel bottom active"
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
				v-model:startFilter="timeStore.startTimeFilter"
				v-model:endFilter="timeStore.endTimeFilter"
				:events="eventsOfInterest"
				:selected-event="eventStore.selectedEvent"
				:hover-event="eventStore.hoveringEvent"
				:mode="mode"
				:show-bars="timeStore.showBars"
				:color-for-event="eventStore.colorForEvent"
				:eventType="eventStore.eventTypeMode"
				:speed-factor="timeStore.speedFactor"
				:class="mode"
				v-model="timeStore.selectedTime"
				@event-selected="eventStore.selectEvent"
				@playing="timeStore.isPlaying = true"
				@paused="timeStore.isPlaying = false"
				@hover="eventStore.setHoveringEvent"
			></TimeReel>
			<button
				v-if="!eventStore.eventSelected && store.viewMode !== 'heatmap'"
				class="panel-expand glassy color"
				@click="toggleTimePanelExpanded"
				v-tooltip="timeStore.timePanelExpanded ? $l.close : $l.showOverview"
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
				:aria-pressed="timeStore.showBars"
				v-tooltip="timeStore.showBars ? $l.hideEventBars : $l.showEventBars"
			>
				<IconChartBar class="bar-icon" aria-hidden="true" />
			</button>
		</div>

		<!-- Event Window -->
		<!-- This is the invisible div that defines where the map should zoom to -->
		<div
			id="event-window"
			:class="{
				eventPanelOn:
					eventStore.selectedEvent !== null && store.viewMode === 'timemachine',
				multiEventPanelOn: store.viewMode === 'heatmap',
			}"
		/>
	</div>
</template>

<style lang="scss">
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

	#focus-frame {
		overflow: hidden;
		transition: all $transition;
		z-index: 200;
		position: absolute;
	}

	#map {
		flex: 1 1 100%;
		height: 100vh;
		min-height: 100vh;
		width: 100vw;
		min-width: 100vw;
	}

	#logo {
		position: absolute;
		top: $panelMargin;
		left: $panelMargin;
		// width: calc(50% - 2 * $panelMargin - $modeButtonWidth);
		height: $headerHeight;
		z-index: 50;
		pointer-events: none;
		background: var(--panel-bg);
		display: flex;
		align-items: center;
		padding: 0.125rem 0.5rem;
		padding: 0.25rem 0.5rem;
		border-radius: $borderRadius;
		border-bottom-right-radius: $borderRadius;
		box-shadow: var(--shadow-md);
		// z-index: 999;

		img {
			height: 100%;
			width: auto;
			margin-right: 0.5rem;
		}

		.eventtype {
			color: var(--primary);
			cursor: pointer;
			pointer-events: auto;
		}
	}

	#mode-toggle {
		position: absolute;
		top: 0;
		left: 50%;
		z-index: 250;
		transform: translateX(-50%) translateY(-1rem);
		transition: transform $transition;
		box-shadow: unset !important;
		&.hidden {
			transform: translateX(-50%) translateY(-150%);
		}
	}

	#hamburger-button {
		position: absolute;
		top: $panelMargin;
		right: $panelMargin;
		border-radius: 100%;
		width: 2.5rem;
		height: 2.5rem;
		padding: 0.5rem;
		z-index: 400;
		box-shadow: var(--shadow-sm), var(--shadow-md);

		&.hidden {
			transform: translateY(-200%);
		}
	}

	#hamburger-menu {
		background: var(--panel-bg);
		backdrop-filter: $frosty;
		top: $panelMargin;
		right: $panelMargin;
		padding: $panelMargin;
		display: flex;
		flex-direction: column;
		gap: $panelMargin;
		z-index: 350;
	}

	$eventGap: calc(
		100% - $smallTimePanelHeight - 4.5 * $panelMargin - 0.5 * $infoHeight -
			$headerHeight
	);
	$eventPanelHeight: calc($eventGap * 0.5 - 0.5 * $panelMargin);
	#event-day-panel {
		position: absolute;
		width: $eventPanelWidth;
		left: $panelMargin;
		height: $eventPanelHeight;
		bottom: calc(3 * $panelMargin + $smallTimePanelHeight + $eventPanelHeight);
	}
	#event-graphs {
		position: absolute;
		width: $eventPanelWidth;
		left: $panelMargin;
		height: $eventPanelHeight;
		bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
		// display: flex;
		// flex-direction: column;
		// justify-content: flex-start;
		// align-items: flex-start;
		// border-radius: 0;
		// backdrop-filter: none;
		// box-shadow: none;
		// background: transparent;

		.subpanel {
			border-radius: $borderRadius;
			backdrop-filter: $frosty;
			box-shadow: var(--shadow-md);
			background: var(--panel-bg);
			flex: 1 1 50%;
			width: 100%;

			&.histo {
				background: var(--panel-bg);
				border-bottom-left-radius: 0;
				border-bottom-right-radius: 0;
				width: 90%;
				box-shadow: var(--shadow-md);
				transition: all $transition;
				// transition: transform 3s;
				&.hidden {
					// transition: transform 3s;
					opacity: 0;
					transform: translateY(120%);
					// transform: scaleY(0) translateY(100%);
				}
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
			background: var(--panel-bg);
			backdrop-filter: $frosty;
			&.hidden {
				opacity: 0;
				transform: translateY(120%);
				// transform: scaleY(0) translateY(100%);
			}
		}
	}

	#multi-button {
		position: absolute;
		top: 0;
		right: $panelMargin;
		border-radius: 100%;
		width: 2.5rem;
		height: 2.5rem;
		padding: 0.5rem;
		z-index: 200;
		box-shadow: var(--shadow-sm), var(--shadow-md);
		transform: translateY(
			calc(100vh - 2 * $panelMargin - $smallTimePanelHeight - 2.5rem)
		);

		&.hidden {
			transform: translateX(200%);
		}

		&.close {
			transform: translateY(
				calc($headerHeight + 2.5 * $panelMargin + $infoHeight)
			);
			&.hidden {
				transform: translate(
					200%,
					calc($headerHeight + 2.5 * $panelMargin + $infoHeight)
				);
			}
		}
	}
	#multimax-button {
		position: absolute;
		top: 0;
		left: 0;
		border-radius: 0;
		border-top-left-radius: $borderRadius;
		border-bottom-right-radius: $borderRadius;
		width: 1.5rem;
		height: 1.5rem;
		padding: 0;
		z-index: 250;
		box-shadow: none !important;
		opacity: 0.5;
		&:hover {
			opacity: 1;
		}

		.tabler-icon {
			width: 1.25rem;
		}
	}
	#multi-event-panel {
		z-index: 150;
		width: calc($infoWidth * 2 + $panelMargin);
		height: calc(
			100vh - 4 * $panelMargin - #{$smallTimePanelHeight} - $infoHeight - 3rem
		);
		right: calc($panelMargin);
		bottom: calc(2 * $panelMargin + #{$smallTimePanelHeight});
		background-color: var(--panel-bg-alt);
		backdrop-filter: $frosty;
		overflow: visible;
		background: var(--panel-bg);
		transition: all $transition;

		&.selected {
			background-color: var(--panel-bg-dark);
		}

		&.maximize {
			width: calc(100% - 2 * $panelMargin);
			height: calc(100vh - 3 * $panelMargin - #{$smallTimePanelHeight} - 3rem);
			right: $panelMargin;
			bottom: calc(2 * $panelMargin + #{$smallTimePanelHeight});
		}
	}

	#info-button {
		position: absolute;
		top: calc($panelMargin + 3rem);
		right: $panelMargin;
		border-radius: 100%;
		width: 2.5rem;
		height: 2.5rem;
		padding: 0.5rem;
		z-index: 300;
		box-shadow: var(--shadow-sm), var(--shadow-md);

		&.hidden {
			transform: translateX(200%);
		}
	}
	#event-info-panel {
		height: $infoHeight !important;
		width: $infoWidth !important;
		z-index: 250;
		transition: all $transition;
		position: absolute;
		top: calc(3rem + 1 * $panelMargin);
		right: $panelMargin;

		.event-info {
			width: 100%;
		}

		transform: translate(0, calc(-150% - 2 * $panelMargin));
		&.show {
			transform: translate(0, 0);
		}
	}
	#selected-event-info-panel {
		z-index: 250;
		transition: all $transition;
		position: absolute;
		top: calc(3rem + $panelMargin);
		right: calc($infoWidth + 2 * $panelMargin);
		transform: translate(0, calc(-250% - 2 * $panelMargin));
		height: $infoHeight !important;
		width: $infoWidth !important;
		&.single {
			// transform: translate(calc(100% - 100vw), calc(-250% - 2 * $panelMargin));
			right: calc(100vw - $eventPanelWidth - $panelMargin);
			width: calc($eventPanelWidth) !important;
			height: calc($infoHeight * 0.5) !important;
		}
		&.show {
			transform: translate(0, 0);
			// &.single {
			// 	transform: translate(calc(100% - 100vw), 0);
			// }
		}
	}

	#time-panel {
		z-index: 150;
		width: calc(100% - 2 * $panelMargin);
		right: $panelMargin;
		bottom: $panelMargin;
		height: $timePanelHeight;
		transition: all $transition;
		border-radius: $borderRadius;
		background: transparent;
		backdrop-filter: none;

		.bar-icon {
			// Manually tweak this icon so that it looks like an event bars icon with the bars offset
			// rather than the normal bar chart icon
			transform: rotate(-90deg);

			path:first-child {
				transform: scaleY(1.5);
				transform-box: fill-box; /* or view-box */
				transform-origin: center;
				vector-effect: non-scaling-stroke;
			}
			path:nth-child(3) {
				transform: scaleY(1) translateY(-3px);
				transform-box: fill-box; /* or view-box */
				transform-origin: center;
				vector-effect: non-scaling-stroke;
			}
			path:last-child {
				display: none;
			}
		}

		&.expanded {
			height: calc(100% - 2 * $panelMargin);
		}

		&.event {
			height: $smallTimePanelHeight;
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;

			&.timemachine {
				background: var(--panel-bg);
			}
		}

		&.heatmap {
			height: $smallTimePanelHeight;
			background-color: var(--panel-bg-alt);
			// transition: height $transition;
		}

		#times {
			width: 100%;
			height: 100%;
			display: flex;
			align-items: center;
			justify-content: center;
			border: none;
			border-radius: $borderRadius;

			.scroller {
				border-radius: $borderRadius !important;
			}
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
			box-shadow: unset;
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

	#multi-button.close,
	#hamburger-button.close,
	#info-button.close {
		border-radius: $borderRadius;
		border-top-left-radius: 0;
		border-bottom-right-radius: 0;
		width: 1.5rem;
		height: 1.5rem;
		padding: 0rem;
		box-shadow: none;
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
			height: calc(100% - 2 * $panelMargin - $smallTimePanelHeight);
		}

		&.multiEventPanelOn {
			height: calc(100% - 2 * $panelMargin - $smallTimePanelHeight);
			width: calc(100% - $multiEventPanelWidth - $panelMargin);
			&.eventPanelOn {
				width: calc(100% - $eventPanelWidth - 2 * $panelMargin);
			}
		}
	}
}
</style>
