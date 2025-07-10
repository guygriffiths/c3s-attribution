<script setup lang="ts">
import { onMounted, Ref, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import Map from './Map.vue'
import Panel from './common/Panel.vue'
import TimeReel from './TimeReel.vue'
import { active } from 'd3'

const $l = useLabels()
const store = useStore()

onMounted(async () => {})
const toggleLabel = computed(() =>
	store.timePanelExpanded ? $l.value.hideTimePanel : $l.value.showTimePanel,
)
</script>

<template>
	<div class="main">
		<Map id="map"></Map>
		<Panel
			id="time-panel"
			:active="store.timePanelExpanded"
			class="bottom peek"
			:class="{ side: store.eventSelected }"
		>
			<TimeReel
				id="times"
				:start="store.startTime"
				:end="store.endTime"
				:events="store.filteredEvents"
				:selected-event="store.selectedEvent"
				v-model="store.selectedTime"
				:changing-filter="store.draggingFilter"
				@event-selected="store.selectEvent"
			></TimeReel>
		</Panel>
		<Panel id="event-frame-panel" class="top" :active="store.eventSelected">
			<div id="event-frame">
				<div class="decor"></div>
			</div>
			<div id="event-info"></div>
		</Panel>
		<Panel id="event-panel" class="top" :active="store.eventSelected">
			<div id="event"></div>
		</Panel>

		<div id="buttons-debug">
			<!-- <h2>{{ store.selectedEvent }}</h2> -->
			<button @click="store.toggleEventSelectedDebug">selectevent</button>
			<button @click="store.selectedTime=new Date(Date.UTC(2022,4,28,0,0,0))">selecttime</button>
		</div>
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

	.panel {
		// opacity: 0.9;
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
	.panel-sideline {
		position: absolute;
		left: -20px;
		z-index: 20;
	}

	#time-panel {
		// width: 100%;
		left: 1.5rem;
		right: 1.5rem;
		bottom: 1.5rem;
		height: 45%;
		z-index: 20;

		transition: all $animTime linear;
		
		&.side {
			left: 50%;
			height: 15%;
			// padding-bottom: calc(15% - 0.75rem);
			border-top: none;
			border-top-right-radius: 0;
			border-top-left-radius: 0;
			border-bottom-left-radius: 0;
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

		#event-frame {
			pointer-events: none;
			flex: 0 0 70%;
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
		bottom: calc(15% + 1.5rem);
		left: 50%;
		border-radius: 0;
		border-top-right-radius: 6px;
		border-bottom: none;
		// box-shadow: rgba(0, 0, 0, 0.5) 3px 0px 3px 0px;
	}
}
</style>
