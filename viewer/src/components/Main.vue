<script setup lang="ts">
import { onMounted, Ref, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import type { FullExtremeEvent } from '@/store/store'
import Map from './Map.vue'
import Panel from './util/Panel.vue'
import TimeReel from './TimeReel.vue'
import { active } from 'd3'
import EventGraphs from './EventGraphs.vue'
import EventInfo from './EventInfo.vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faChevronUp,
	faAnglesUp,
	faWandMagicSparkles,
	faClose,
	faChevronDown,
} from '@fortawesome/free-solid-svg-icons'
import RegionPanel from './RegionPanel.vue'

const $l = useLabels()
const store = useStore()

onMounted(async () => {})
const toggleLabel = computed(() =>
	store.timePanelVisible ? $l.value.hideTimePanel : $l.value.showTimePanel,
)
const toggleTimePanelExpanded = () => {
	store.timePanelExpanded = !store.timePanelExpanded
	if (store.timePanelExpanded) {
		store.timePanelVisible = true
	}
}
</script>

<template>
	<div class="main">
		<Map id="map"></Map>
		<Panel
			id="time-panel"
			:active="store.timePanelVisible || store.eventSelected"
			class="bottom peek"
			:class="{
				event: store.eventSelected,
				expanded: store.timePanelExpanded,
				region: !store.eventSelected && store.exploringRegion,
			}"
		>
			<TimeReel
				id="times"
				:start="store.startTime"
				:end="store.endTime"
				:events="store.filteredEvents"
				:day-counts="store.dayCounts"
				:selected-event="store.selectedEvent"
				v-model="store.selectedTime"
				:changing-filter="store.draggingFilter"
				@event-selected="store.selectEvent"
				:exploring="store.timePanelExpanded"
				:vertical="store.exploringRegion"
			></TimeReel>
			<button
				class="panel-hide"
				@click="toggleTimePanelExpanded"
				v-show="!store.eventSelected && !store.exploringRegion"
			>
				<font-awesome-icon
					:icon="!store.timePanelExpanded ? faChevronUp : faAnglesUp"
					:class="{ 'fa-rotate-180': store.timePanelVisible }"
				/>
			</button>
			<button
				v-if="store.timePanelVisible"
				class="panel-expand"
				@click="toggleTimePanelExpanded"
				v-show="!store.eventSelected && !store.exploringRegion"
			>
				<font-awesome-icon
					:icon="!store.timePanelExpanded ? faWandMagicSparkles : faChevronDown"
				/>
			</button>
		</Panel>
		<Panel id="event-frame-panel" class="top" :active="store.eventSelected">
			<button class="close-button" @click="store.selectEvent(null)">
				<font-awesome-icon :icon="faClose" />
			</button>
			<button
				class="explore-button"
				@click="console.log('explore local events')"
			>
				<font-awesome-icon :icon="faWandMagicSparkles" />
			</button>
			<div id="event-frame">
				<div class="decor"></div>
			</div>
			<EventInfo
				id="event-info"
				:selected-event="store.selectedEvent"
			></EventInfo>
		</Panel>
		<Panel id="event-panel" class="top" :active="store.eventSelected">
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
				:selected-event="store.selectedEvent"
				:time="store.selectedTime"
				@date-selected="store.selectedTime = $event"
			></EventGraphs>
		</Panel>
		<RegionPanel
			id="region-panel"
			class="left"
			:active="store.exploringRegion"
			@close="store.filters.wrafRegion = null"
		></RegionPanel>
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
	.panel-expand,
	.panel-hide {
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

	#time-panel {
		width: calc(100% - 2 * $panelMargin);
		left: $panelMargin;
		bottom: $panelMargin;
		height: 40%;
		&.expanded {
			height: calc(100% - 2 * $panelMargin);
		}

		z-index: 20;

		transition: all $animTime linear;

		&.event {
			left: 50%;
			width: calc(50% - $panelMargin);
			height: $eventTimePanelHeight;
			// padding-bottom: calc(15% - 0.75rem);
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;
		}

		&.region {
			left: $panelMargin;
			bottom: $panelMargin;
			height: calc(100% - 2 * $panelMargin);
			width: $vTimePanelWidth;
			box-shadow: none;
			border-top-right-radius: 0;
			border-bottom-right-radius: 0;
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
		top: 1.5rem;
		right: 1.5rem;
		bottom: calc($eventTimePanelHeight + 1.5rem);
		left: 50%;
		border-radius: 0;
		border-top-right-radius: 6px;
		border-bottom: none;
		padding-top: 1rem;
		display: flex;
		// box-shadow: rgba(0, 0, 0, 0.5) 3px 0px 3px 0px;
	}

	#region-panel {
		width: calc(100% - 2 * $panelMargin);
		height: calc(100% - 2 * $panelMargin);
		padding-left: $vTimePanelWidth;
		top: $panelMargin;
		left: $panelMargin;
		// bottom: $panelMargin;;
		// right: $panelMargin;;
	}
}
</style>
