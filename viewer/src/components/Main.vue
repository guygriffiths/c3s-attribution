<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import Map from './Map.vue'
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
} from '@fortawesome/free-solid-svg-icons'
import FocusFrame from './util/FocusFrame.vue'
import EventRanker from './util/EventRanker.vue'

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
const toggleTimePanelHidden = () => {
	store.timePanelVisible = !store.timePanelVisible
	// if (!store.timePanelVisible) {
	// 	store.timePanelExpanded = false
	// }
}

const exitFocus = () => {
	store.selectEvent(null)
	store.filters.wrafRegion = null
	store.selectedPointFilter = null
	store.draggingFilter = false
}
</script>

<template>
	<div class="main">
		<FocusFrame
			class="focus-frame"
			:active="store.isFocused"
			@close="exitFocus"
		/>
		<Map id="map"></Map>
		<Panel
			id="time-panel"
			:active="store.timePanelVisible || store.eventSelected"
			class="bottom peek"
			:class="{
				event: store.eventSelected,
				expanded: store.timePanelExpanded,
				heatmap: store.viewMode === 'heatmap',
				focused: store.isFocused,
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
				@event-selected="store.selectEvent"
				:exploring="store.timePanelExpanded"
				:vertical="store.viewMode === 'heatmap'"
				:show-bars="store.showBars"
			></TimeReel>
			<button
				v-if="!store.eventSelected && store.viewMode !== 'heatmap'"
				class="panel-hide"
				@click="toggleTimePanelHidden"
			>
				<font-awesome-icon
					:icon="!store.timePanelExpanded ? faChevronUp : faAnglesUp"
					:class="{ 'fa-rotate-180': store.timePanelVisible }"
				/>
			</button>
			<button
				v-if="
					store.timePanelVisible &&
					!store.eventSelected &&
					store.viewMode !== 'heatmap'
				"
				class="panel-expand"
				@click="toggleTimePanelExpanded"
			>
				<font-awesome-icon
					:icon="!store.timePanelExpanded ? faWandMagicSparkles : faClose"
				/>
			</button>
			<button
				v-if="store.viewMode === 'explore' && !store.timePanelExpanded"
				class="show-bars"
				:class="{ active: store.showBars }"
				@click="store.showBars = !store.showBars"
			>
				<font-awesome-icon :icon="faBarsStaggered" />
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
		<Panel
			id="region-panel"
			class="bottom"
			:class="{ dragging: store.draggingFilter }"
			:active="store.exploringRegion"
		>
			<EventRanker :sort-func="(a, b) => b.duration - a.duration" :topN="5" />
			<EventRanker
				:sort-func="(a, b) => b.pixel_count - a.pixel_count"
				:topN="5"
			/>
			<EventRanker
				:sort-func="(a, b) => b.peak_value - a.peak_value"
				:topN="5"
			/>
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
		transition: all $settleTime ease-in-out;
		z-index: 20;
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
		width: calc(100% - 2 * $panelMargin);
		right: $panelMargin;
		bottom: $panelMargin;
		height: 40%;
		&.expanded {
			height: calc(100% - 2 * $panelMargin);
		}

		z-index: 20;

		transition: all $animTime linear;

		&.event {
			width: calc(50% - $panelMargin);
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
			height: calc(100% - 4 * $panelMargin - 1rem);
			width: $vTimePanelWidth;
			box-shadow: none;
			border-bottom-left-radius: 0;

			.time-reel {
				border-bottom-left-radius: 0;
			}

			&.focused {
				right: calc(2 * $panelMargin);
				bottom: calc(2 * $panelMargin);
				height: calc(100% - 6 * $panelMargin - 1rem);
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
		width: calc(100% - 4 * $panelMargin);
		height: calc(40% - 2 * $panelMargin);
		bottom: calc(2 * $panelMargin);
		left: calc(2 * $panelMargin);
		// bottom: $panelMargin;;
		// right: $panelMargin;;
		display: flex;
		flex-direction: row;
		padding: calc(3 * $panelMargin);
		padding-right: $vTimePanelWidth;

		&.dragging {
			opacity: 0.5;
			pointer-events: none;
		}

		.event-ranker {
			flex: 1 1 33%;
			margin-right: 1rem;
			border-radius: 0.5rem;
			background-color: rgba($panelBg, 0.75);
			box-shadow: rgba(0, 0, 0, 0.2) 0px 4px 6px -1px,
				rgba(0, 0, 0, 0.1) 0px 2px 4px -1px;
			// border: 1px solid rgba(0, 0, 0, 0.1);
			// border: 1px solid rgba(255, 255, 255, 0.1);
			// backdrop-filter: blur(5px);
			height: 100%;
			min-width: 0; // allow flexbox to shrink it
			padding: 0.5rem;
		}
	}
}
</style>
