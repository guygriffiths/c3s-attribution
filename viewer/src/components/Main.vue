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
import { differenceInDays } from 'date-fns'
import MultiEventSmartPanel from './MultiEventSmartPanel.vue'
import {
	IconCalendarWeek,
	IconCalendarTime,
	IconChartBar,
	IconChartHistogram,
	IconChevronCompactUp,
	IconInfoSquareRounded,
	IconMenu2,
	IconWindowMaximize,
	IconWindowMinimize,
	IconX,
	IconLayersIntersect,
	IconEye,
	IconEyePin,
} from '@tabler/icons-vue'
import EventDayPanel from './EventDayPanel.vue'
import {
	getCurrentEvents,
	getParameterFilteredEvents,
	getSpaceTimeFilteredEvents,
	getSpatiallyFilteredEvents,
	getTimeFilteredEvents,
	onParameterFilterChanged,
	onSpatialFilterChanged,
	onTimeFilterChanged,
	setEventTypeFilter,
	setTimeRangeFilter,
} from '@/lib/eventsDB'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

const toggleTimePanelExpanded = () => {
	timeStore.timePanelExpanded = !timeStore.timePanelExpanded
}

const exitFocus = () => {
	eventStore.selectEvent(null)
	store.draggingFilter = false
}

// Time reel events. These are filtered spatially and manually, but not temporally
const timeReelEvents = ref([] as ExtremeEvent[])
onSpatialFilterChanged(() => {
	timeReelEvents.value = getSpatiallyFilteredEvents()
})
watch(
	() => [store.exploreGlobal],
	() => {
		if (store.exploreGlobal) {
			timeReelEvents.value = getParameterFilteredEvents()
		} else {
			timeReelEvents.value = getSpatiallyFilteredEvents()
		}
	},
	{ immediate: true },
)

// Summary events. These are filtered spatially, manually, and temporally (either at a day - timemchine, or over a range - heatmap)
const summaryEvents = ref([] as ExtremeEvent[])
onTimeFilterChanged(() => {
	if (store.viewMode === 'timemachine') {
		summaryEvents.value = getCurrentEvents(timeStore.selectedTime, true)
	} else {
		summaryEvents.value = getSpaceTimeFilteredEvents()
		if (eventStore.selectedEvent) {
			// Ensure selected event is included
			if (
				!summaryEvents.value.find((e) => e.id === eventStore.selectedEvent?.id)
			) {
				// @ts-ignore
				summaryEvents.value.push(eventStore.selectedEvent)
			}
		}
	}
})
watch(
	() => [store.viewMode, timeStore.selectedTime],
	() => {
		if (store.viewMode === 'timemachine') {
			summaryEvents.value = getCurrentEvents(timeStore.selectedTime, true)
		} else {
			summaryEvents.value = getSpaceTimeFilteredEvents()
			if (eventStore.selectedEvent) {
				// Ensure selected event is included
				if (
					!summaryEvents.value.find(
						(e) => e.id === eventStore.selectedEvent?.id,
					)
				) {
					// @ts-ignore
					summaryEvents.value.push(eventStore.selectedEvent)
				}
			}
		}
	},
	{ immediate: true },
)
// Used as background events in MultiEventSmartPanel when filtering spatially
const globalFilteredEvents = ref([] as ExtremeEvent[])

onParameterFilterChanged(() => {
	globalFilteredEvents.value = getParameterFilteredEvents()
	if (store.exploreGlobal) {
		// console.log('Main.vue: setting eventsOfInterest to globalFilteredEvents')
		timeReelEvents.value = globalFilteredEvents.value
	}
})

let pending = false
watch(
	() => [timeStore.startTimeFilter, timeStore.endTimeFilter],
	() => {
		setTimeRangeFilter(timeStore.startTimeFilter, timeStore.endTimeFilter)
	},
	{ immediate: true },
)

watch(
	() => [eventStore.eventTypeMode],
	() => {
		if (eventStore.eventTypeMode === 'cold') {
			setEventTypeFilter(false, true)
		} else if (eventStore.eventTypeMode === 'hot') {
			setEventTypeFilter(true, false)
		} else {
			setEventTypeFilter(true, true)
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
			<div class="title-wrapper" :class="{ square: store.mainHelpOpen }">
				<img
					src="@/assets/img/c3s-logo.png"
					alt="C3S Logo"
					aria-hidden="true"
				/>
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
					<button
						class="expand glassy color"
						@click="store.mainHelpOpen = !store.mainHelpOpen"
						v-tooltip="$l.help"
						:class="{ disabled: store.mainHelpOpen }"
					>
						<IconInfoSquareRounded size="20" aria-hidden="true" />
					</button>
				</h1>
			</div>
			<div class="welcome" :class="{ hidden: !store.mainHelpOpen }">
				<div class="scroll-wrap">
					<p>
						Welcome to the C3S Extreme Event Explorer! Explore extreme
						temperature events from {{ new Date().getFullYear() }} all the way
						back to 1979.
					</p>
					<p>
						This is a prototype tool developed as part of the Copernicus Climate
						Change Service (C3S). When the final version is released in Spring
						2026, it will feature fuller interactive help. For now, a brief
						overview of the main features is provided below.
					</p>
					<h3>
						<button class="glassy color decoration">
							<IconCalendarTime size="24" aria-hidden="true" />
						</button>
						Time Machine - Navigate through time effortlessly and explore
						individual events in detail
					</h3>
					<ul>
						<li>
							Use the time reel to intuitively and quickly navigate through
							time.
							<ul>
								<li>Scroll through years with your mouse or trackpad</li>
								<li>
									Click and drag the reel to scrub through the selected year
								</li>
								<li>
									Use the navigation buttons to step through time, or animate
									the passing of time
								</li>
								<li>
									Explore the full timeline and use the scrubber to quickly
									explore and jump to specific dates
								</li>
								<li>
									Select events directly from the time reel to jump to the start
									of that event and see it in more detail
								</li>
							</ul>
						</li>
						<li>
							See a daily summary of events, ranked by either size, temperature,
							or duration
						</li>
						<li>
							Select an event from the daily ranking, the map, or the time reel
							to see detailed graphs and information, and to download the raw
							event data
						</li>
						<li>
							Filter events or explore extreme cold events using the hamburger
							menu
						</li>
					</ul>
					<h3>
						<button class="glassy color decoration">
							<IconEyePin size="24" aria-hidden="true" />
						</button>
						Overview - Visualise thousands of historical events simultaneously
					</h3>
					<ul>
						<li>
							Select a time range to view the footprints of thousands of events
							at once
							<ul>
								<li>
									The time reel has now transformed into a single timeline of
									events
								</li>
								<li>
									By default the last 20 years are selected, but the sliding
									window can be moved and resized
								</li>
								<li>
									The map and graphs will update in real-time as you adjust the
									time range
								</li>
								<li>
									Trends over time can easily be visualised by using the
									animation controls
								</li>
							</ul>
						</li>
						<li>
							Select a particular geographical region to focus on
							<ul>
								<li>
									Draw a region on the map to filter events whose pixels lie
									within it
								</li>
								<li>
									Use the point selector to focus on events at a specific
									location
								</li>
								<li style="font-style: italic; opacity: 0.8">
									Coming spring 2026: Upload GeoJSON regions for accurate custom
									filtering
								</li>
							</ul>
						</li>
						<li>
							The summary will now show not just a selected daily ranking, but a
							ranking of all events in the selected time range
						</li>
						<li>
							View histograms and plots of event characteristics over the
							selected time range
						</li>
						<li>
							Select an event from the ranking table, or from Time Machine mode,
							to see its entire footprint of extreme temperatures, and to see it
							put into context on the graphs and ranking table.
						</li>
					</ul>
				</div>
				<button
					class="glassy collapse"
					@click="store.mainHelpOpen = false"
					v-tooltip="$l.close"
				>
					<IconChevronCompactUp size="24" aria-hidden="true" />
				</button>
			</div>
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
			:inert="
				store.isFocused || timeStore.timePanelExpanded ? 'true' : undefined
			"
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
			:events-of-interest="summaryEvents"
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
				!store.showMultiPanel || store.viewMode !== 'heatmap'
					? 'true'
					: undefined
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
					: undefined
			"
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
			:events-of-interest="summaryEvents"
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
					: undefined
			"
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
				eventStore.selectedEvent === null || !store.showInfoPanel
					? 'true'
					: undefined
			"
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
				:events="timeReelEvents"
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
		z-index: 200;
		pointer-events: none;
		display: flex;
		flex-direction: column;
		gap: 0;

		button.expand {
			position: absolute;
			bottom: 0;
			right: 0;
			padding: 0;
			transform: translate(50%, 50%);
			display: flex;
			pointer-events: all;
			transition: all $animTime $animEase $animTime;
			z-index: 10;
			&.disabled {
				transition: all 0 $animEase;
				opacity: 0;
				pointer-events: none;
			}

			svg {
				margin: 0;
			}
		}
		align-items: flex-start;
		.title-wrapper {
			z-index: 5;
			background: var(--panel-bg);
			border-radius: $borderRadius;
			box-shadow: var(--shadow-md);
			backdrop-filter: $frosty;
			padding: 0.25rem 0.5rem;
			display: flex;
			align-items: center;
			height: $headerHeight;
			transition: all $animTime $animEase $animTime;

			&.square {
				transition: all 0s $animEase;
				border-bottom-left-radius: 0;
				border-bottom-right-radius: 0;
				box-shadow: none;
			}

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

		.welcome {
			max-width: max(40vw, 500px);
			z-index: 0;
			pointer-events: all;
			font-size: 0.875rem;
			line-height: 1.25rem;
			display: flex;
			flex-direction: column;
			// align-items: center;
			background: var(--panel-bg);
			border-radius: $borderRadius;
			box-shadow: var(--shadow-md);
			backdrop-filter: $frosty;
			border-top-left-radius: 0;
			font-size: 1.1rem;

			.scroll-wrap {
				padding: 0 0.5rem;
				overflow-y: auto;
			}
			h2 {
				margin: 0 0 0rem 0;
				font-size: 1.2rem;
			}
			h3 {
				font-size: 1.1rem;
				margin: 0.5rem 0 0.5rem 0;
				display: flex;
				align-items: center;
				button.decoration {
					margin-right: 0.5rem;
				}
			}
			ul {
				padding-left: 1.25rem;
				margin: 0;
			}
			button.decoration {
				pointer-events: none;
				margin: 0;
				padding: 2px;
				width: 2rem;
				box-shadow: none;
			}
			button.collapse {
				pointer-events: all;
				height: 1.25rem;
				width: 100%;
				padding: 0;
				border-top-left-radius: 0;
				border-top-right-radius: 0;
				margin-top: auto;
				position: sticky;
			}

			flex: 1 1 auto;
			max-height: calc(100vh - $headerHeight - 3 * $panelMargin);
			height: calc(100vh - $headerHeight - 3 * $panelMargin);
			transition: all $transition;
			&.hidden {
				overflow: hidden;
				padding: 0;
				// opacity: 0;
				max-height: 0;
			}
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
		100vh - $smallTimePanelHeight - 4 * $panelMargin - 0.5 * $infoHeight -
			$headerHeight
	);
	$eventPanelHeight: calc($eventGap * 0.5 - $panelMargin);
	#event-day-panel {
		position: absolute;
		width: $eventPanelWidth;
		left: $panelMargin;
		height: $eventPanelHeight;
		bottom: calc(3 * $panelMargin + $smallTimePanelHeight + $eventPanelHeight);
		z-index: 150;
	}
	#event-graphs {
		position: absolute;
		width: $eventPanelWidth;
		left: $panelMargin;
		height: $eventPanelHeight;
		bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
		z-index: 150;
		// display: flex;
		// flex-direction: column;
		// justify-content: flex-start;
		// align-items: flex-start;
		// border-radius: 0;
		// backdrop-filter: none;
		// box-shadow: none;
		// background: transparent;
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
				calc($headerHeight + 3 * $panelMargin + $infoHeight)
			);
			&.hidden {
				transform: translate(
					200%,
					calc($headerHeight + 3 * $panelMargin + $infoHeight)
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
		z-index: 180;
		width: calc($infoWidth * 2 + $panelMargin);
		height: calc(
			100vh - 5 * $panelMargin - #{$smallTimePanelHeight} - $infoHeight - 3rem
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
		top: calc($headerHeight + 2 * $panelMargin);
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
		z-index: 150;
		transition: all $transition;
		position: absolute;
		top: calc($headerHeight + 2 * $panelMargin);
		right: $panelMargin;

		.event-info {
			width: 100%;
		}

		transform: translate(0, calc(-200% - 2 * $panelMargin));
		&.show {
			transform: translate(0, 0);
		}
	}
	#selected-event-info-panel {
		z-index: 150;
		transition: all $transition;
		position: absolute;
		top: calc($headerHeight + 2 * $panelMargin);
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
