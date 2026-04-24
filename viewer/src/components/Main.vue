<script setup lang="ts">
import { computed } from 'vue'
import { differenceInDays } from 'date-fns'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { colorForValue, useStore as useEventStore } from '@/store/eventStore'
import { helpMe } from '@/lib/help'
import MapComponent from './Map.vue'
import AppLogo from './AppLogo.vue'
import FooterLogos from './FooterLogos.vue'
import EventTypeToggle from './util/EventTypeToggle.vue'
import TimeReel from './TimeReel.vue'
import EventGraphs from './EventGraphs.vue'
import EventInfoPanel from './EventInfoPanel.vue'
import SelectedEventInfoPanel from './SelectedEventInfoPanel.vue'
import FilterPanel from './FilterPanel.vue'
import FocusFrame from './util/FocusFrame.vue'
import ModeToggle from './util/ModeToggle.vue'
import MultiEventSmartPanel from './MultiEventSmartPanel.vue'
import EventDayPanel from './EventDayPanel.vue'
import HelpButton from './util/HelpButton.vue'
import ColorScale from './ColorScale.vue'
import {
	IconCalendarWeek,
	IconChartBar,
	IconChartHistogram,
	IconInfoSquareRounded,
	IconMenu2,
	IconWindowMaximize,
	IconWindowMinimize,
	IconX,
	IconInfoOctagon,
} from '@tabler/icons-vue'
import { useEventFilters } from '@/lib/eventFilters'
import { interpolateCool } from 'd3'
import { interpolateColorCold, interpolateColorHot } from '@/lib/utils'
import { c3sred, c3sblue } from '@/assets/styles/scssVars.module.scss'

// Stores
const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

// UI state handlers
const toggleTimePanelExpanded = () => {
	timeStore.timePanelExpanded = !timeStore.timePanelExpanded
}

const exitFocus = () => {
	eventStore.selectEvent(null)
	store.draggingFilter = false
}

const { timeReelEvents, summaryEvents, globalFilteredEvents } =
	useEventFilters()

// Time reel mode computation
const mode = computed((): TimeReelMode => {
	if (store.viewMode === 'heatmap') return 'timeline'
	if (eventStore.eventSelected) return 'eventzoom'
	if (timeStore.timePanelExpanded) return 'overview'
	return 'default'
})

// Selected day index for event day panel
const selectedDayIdx = computed((): number | null => {
	if (
		!eventStore.selectedEvent ||
		!eventStore.selectedEvent.hasOwnProperty('pixel_max_values')
	) {
		return null
	}

	const totalDays = eventStore.durationForEvent(eventStore.selectedEvent)
	const selectedDay = differenceInDays(
		timeStore.selectedTime,
		new Date(eventStore.selectedEvent?.times[0] || 0),
	)

	if (selectedDay < 0 || selectedDay >= totalDays) return null
	return selectedDay
})

const hotScaleOn = computed(() => {
	if (store.viewMode === 'timemachine') {
		return eventStore.eventTypeMode.indexOf('hot') > -1
	} else {
		return eventStore.selectedEvent?.event_type === 'hot'
	}
})

const coldScaleOn = computed(() => {
	if (store.viewMode === 'timemachine') {
		return `${eventStore.eventTypeMode}`.indexOf('cold') > -1
	} else {
		return eventStore.selectedEvent?.event_type === 'cold'
	}
})

const hotHeatmapOn = computed(() => {
	return (
		store.viewMode === 'heatmap' && eventStore.eventTypeMode.indexOf('hot') > -1
	)
})

const coldHeatmapOn = computed(() => {
	return (
		store.viewMode === 'heatmap' &&
		eventStore.eventTypeMode.indexOf('cold') > -1
	)
})

const withAlpha = (hslColor: string, alpha: number): string => {
	if (hslColor.startsWith('hsl(') && hslColor.endsWith(')')) {
		return `hsla(${hslColor.slice(4, -1)} , ${alpha})`
	}
	return hslColor
}

const getStackedC3sRed = (value: number): string => {
	const layers = Math.max(0, Math.min(50, Math.round(value)))
	const singleLayerAlpha = 0.1
	const effectiveAlpha = 1 - Math.pow(1 - singleLayerAlpha, layers)
	return withAlpha(c3sred, effectiveAlpha)
}

const getStackedC3sBlue = (value: number): string => {
	const layers = Math.max(0, Math.min(50, Math.round(value)))
	const singleLayerAlpha = 0.1
	const effectiveAlpha = 1 - Math.pow(1 - singleLayerAlpha, layers)
	return withAlpha(c3sblue, effectiveAlpha)
}
</script>

<template>
	<div class="main">
		<!-- Focus overlay frame -->
		<FocusFrame id="focus-frame" :active="store.isFocused" @close="exitFocus" />

		<!-- Main map component -->
		<MapComponent id="map" />

		<div
			id="color-scale"
			class="panel"
			:class="{
				selected: store.isFocused,
				timemachine: store.viewMode === 'timemachine',
			}"
		>
			<ColorScale
				:colorfunc="
					(val: number) => colorForValue(val, true, eventStore.hotScale)
				"
				:domain="eventStore.hotScale.domain()"
				:label="eventStore.eventSelected ? $l.cellTemp : $l.eventMax"
				:units="eventStore.heatIntensityUnits"
				v-if="hotScaleOn"
			/>
			<ColorScale
				:colorfunc="
					(val: number) => colorForValue(val, false, eventStore.coldScale)
				"
				:domain="eventStore.coldScale.domain()"
				:units="eventStore.coldIntensityUnits"
				:label="eventStore.eventSelected ? $l.cellTemp : $l.eventMin"
				v-if="coldScaleOn"
			/>
			<ColorScale
				:colorfunc="getStackedC3sRed"
				:domain="[0, 100]"
				label="events"
				v-if="hotHeatmapOn"
			/>
			<ColorScale
				:colorfunc="getStackedC3sBlue"
				:domain="[0, 100]"
				label="events"
				v-if="coldHeatmapOn"
			/>
		</div>

		<!-- Logo and title section -->
		<AppLogo id="logo" />

		<!-- Mode toggle (time machine / overview) -->
		<ModeToggle
			v-model="store.viewMode"
			id="mode-toggle"
			:class="{ hidden: timeStore.timePanelExpanded }"
		/>

		<!-- Hamburger menu button -->
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

		<!-- Hamburger menu panel -->
		<div
			id="hamburger-menu"
			class="panel top"
			:class="{ active: store.hamburgerMenuOpen && !store.isFocused }"
			:inert="!store.hamburgerMenuOpen ? 'true' : undefined"
		>
			<div class="menu-section">
				<h2>{{ $l.chooseEventType }}</h2>
				<EventTypeToggle
					:model-value="eventStore.eventTypeMode"
					@update:model-value="eventStore.setEventTypeMode"
				/>
			</div>
			<div class="menu-section">
				<h2>{{ $l.chooseFilters }}</h2>
				<FilterPanel v-model="eventStore.filters" />
			</div>
			<button
				class="about-button glassy color"
				@click="helpMe('aboutInfo')"
				v-tooltip="$l.aboutInfo"
			>
				<IconInfoOctagon size="24" aria-hidden="true" />{{ $l.aboutInfo }}
			</button>
			<!-- <HelpButton help="hamburgerMenu" /> -->
		</div>

		<!-- Event day panel (time machine mode, left side) -->
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
		>
			<HelpButton help="eventDayPanel" />
		</EventDayPanel>

		<!-- Event graphs panel (time machine mode, left side) -->
		<EventGraphs
			id="event-graphs"
			:selected-event="eventStore.selectedEvent"
			:event-store="eventStore"
			class="panel left chart event-graphs-help"
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
		>
			<HelpButton help="eventGraphs" />
		</EventGraphs>

		<!-- Multi-event panel toggle button -->
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

		<!-- Multi-event panel (overview mode, right side) -->
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
		>
			<button
				id="multimax-button"
				class="glassy color"
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
			<HelpButton help="multiEventPanel" />
		</MultiEventSmartPanel>

		<!-- Event info panel toggle button -->
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

		<!-- Event info panel (right side, top) -->
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
			<HelpButton help="eventInfo" />
		</EventInfoPanel>

		<!-- Selected event info panel (dependent upon mode - RHS in timemachine, LHS in heatmap) -->
		<SelectedEventInfoPanel
			v-if="eventStore.selectedEvent"
			id="selected-event-info-panel"
			class="chart"
			:selected-event="eventStore.selectedEvent"
			:event-store="eventStore"
			:class="{
				show:
					eventStore.selectedEvent !== null &&
					(store.showInfoPanel || store.viewMode === 'timemachine'),
				single: store.viewMode === 'timemachine' && store.isFocused,
			}"
			:inert="
				eventStore.selectedEvent === null ||
				!(store.showInfoPanel && store.viewMode === 'timemachine')
					? 'true'
					: undefined
			"
		>
			<HelpButton help="selectedEventInfo" />
		</SelectedEventInfoPanel>

		<!-- Time panel (bottom) -->
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
			/>

			<!-- Time panel expand button -->
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
				<IconX v-else aria-hidden="true" />
			</button>

			<!-- Show bars toggle -->
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

			<HelpButton help="timeReel" />
		</div>

		<!-- Footer logos -->
		<FooterLogos id="footer-logos" />

		<!-- Event window (invisible div for map zoom boundaries) -->
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

	#color-scale {
		position: absolute;
		bottom: $panelMargin * 0.5;
		left: $panelMargin * 0.5;
		z-index: 350;
		padding: 0.5rem;
		width: calc(0.5 * (100vw - 35rem - 2 * $panelMargin));
		background: var(--panel-bg);
		gap: 0.5rem;
		transition: all $transition;

		&.selected {
			bottom: calc($panelMargin + $smallTimePanelHeight + $panelMargin);
			left: $panelMargin;
			display: flex;
		}

		&.timemachine {
			display: flex;
			&.selected {
				left: calc(50vw + 0.5 * 35rem);
			}
		}
	}

	#footer-logos {
		position: absolute;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		z-index: 325;
		width: 35rem;
	}

	#focus-frame {
		overflow: hidden;
		transition: all $transition;
		z-index: 500;
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
		z-index: 200;
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
		padding: $panelMargin * 0.5;
		display: flex;
		flex-direction: column;
		justify-content: stretch;
		align-items: stretch;;
		gap: $panelMargin * 0.5;
		z-index: 350;

		.about-button {
			margin-top: auto;
			display: flex;
			align-items: center !important;
			justify-content: center;
			gap: 0.5rem;
		}

		.menu-section {
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
			padding: 0;

			h2 {
				font-size: 1rem;
				margin: 0.25rem 0 0 0;
			}
		}
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
			100vh - 5 * $panelMargin - $smallTimePanelHeight - $infoHeight - 3rem
		);
		right: calc($panelMargin);
		bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
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
			height: calc(
				100vh - 4 * $panelMargin - $smallTimePanelHeight - $headerHeight
			);
			right: $panelMargin;
			bottom: calc(2 * $panelMargin + $smallTimePanelHeight);
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
		transform: translate(0, calc(-200% - 2 * $panelMargin));

		.event-info {
			width: 100%;
		}

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
			right: calc(100vw - $eventPanelWidth - $panelMargin);
			width: calc($eventPanelWidth) !important;
			height: calc($infoHeight * 0.5) !important;
		}

		&.show {
			transform: translate(0, 0);
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

		&.expanded {
			height: calc(100% - 2 * $panelMargin);
			z-index: 350;
		}

		&.event {
			z-index: 350;
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
		}

		&.expanded {
			.panel-expand {
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

	.panel {
		.help-button {
			opacity: 0;
			pointer-events: none;
			transition: opacity $animTime $animEase;
		}
	}

	.panel:hover,
	.panel:focus {
		.help-button {
			opacity: 1;
			pointer-events: all;
		}
	}
}
</style>
