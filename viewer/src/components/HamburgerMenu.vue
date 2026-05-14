<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import { usePersistentStore } from '@/store/persistentStore'
import { useLabels } from '@/lib/labels'
import EventTypeToggle from './util/EventTypeToggle.vue'
import FilterPanel from './FilterPanel.vue'
import {
	IconMenu2,
	IconX,
	IconRainbow,
	IconPlayerPlay,
	IconPlayerTrackNext,
} from '@tabler/icons-vue'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()
const persistentStore = usePersistentStore()

const SPEEDS = [0.25, 0.5, 1, 2, 4]

const speedIndex = computed(() => {
	const i = SPEEDS.indexOf(timeStore.speedFactor)
	return i >= 0 ? i : 2 // default to index 2 = 1×
})

const onSpeedInput = (e: Event) => {
	timeStore.speedFactor = SPEEDS[Number((e.target as HTMLInputElement).value)]
}
</script>

<template>
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
		<div class="menu-section speed-section">
			<h2>Animation Speed</h2>
			<div class="speed-row">
				<IconPlayerPlay class="speed-icon" :size="16" aria-hidden="true" />
				<div class="speed-slider-wrap">
					<input
						type="range"
						class="speed-slider"
						min="0"
						max="4"
						step="1"
						:value="speedIndex"
						@input="onSpeedInput"
					/>
					<div class="speed-ticks" aria-hidden="true">
						<span v-for="i in 5" :key="i" class="tick" />
					</div>
				</div>
				<IconPlayerTrackNext class="speed-icon" :size="16" aria-hidden="true" />
			</div>
		</div>
		<div v-if="persistentStore.allHardComplete" class="menu-section rainbow-section">
			<h2>Rainbow Mode</h2>
			<button
				class="rainbow-toggle"
				:class="{ active: persistentStore.rainbowMode }"
				@click="persistentStore.setRainbowMode(!persistentStore.rainbowMode)"
			>
				<IconRainbow size="18" aria-hidden="true" />
				{{ persistentStore.rainbowMode ? 'Disable' : 'Enable' }} Rainbow Mode
			</button>
		</div>
	</div>
</template>

<style lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.main {
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
		align-items: stretch;
		gap: $panelMargin * 0.5;
		z-index: 350;

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

		.speed-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.speed-row {
			display: flex;
			align-items: center;
			gap: 0.5rem;
		}

		.speed-icon {
			flex-shrink: 0;
			opacity: 0.55;
		}

		.speed-slider-wrap {
			flex: 1;
			display: flex;
			flex-direction: column;
			gap: 3px;
		}

		.speed-slider {
			width: 100%;
			appearance: none;
			-webkit-appearance: none;
			height: 4px;
			border-radius: 2px;
			background: var(--divider);
			outline: none;
			cursor: pointer;
			accent-color: var(--primary);

			&::-webkit-slider-thumb {
				-webkit-appearance: none;
				width: 14px;
				height: 14px;
				border-radius: 50%;
				background: var(--primary);
				cursor: pointer;
				border: none;
			}

			&::-moz-range-thumb {
				width: 14px;
				height: 14px;
				border-radius: 50%;
				background: var(--primary);
				cursor: pointer;
				border: none;
			}
		}

		.speed-ticks {
			display: flex;
			justify-content: space-between;
			padding: 0 7px; // half of 14px thumb width — aligns ticks under thumb centres

			.tick {
				width: 1px;
				height: 4px;
				background: var(--text-tertiary);
				opacity: 0.4;
				border-radius: 1px;
			}
		}

		.rainbow-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.rainbow-toggle {
			display: flex;
			align-items: center;
			gap: 0.5rem;
			padding: 0.375rem 0.75rem;
			border-radius: 6px;
			border: 1px solid var(--divider);
			background: none;
			cursor: pointer;
			font-size: 0.875rem;
			color: inherit;
			transition: background $animTime $animEase, color $animTime $animEase;

			&.active {
				background: linear-gradient(100deg, $c3sred, $c3sorange, $lightbulb, $c3sgreen, $c3steal, $c3sblue, $c3spurple);
				color: white;
				border-color: transparent;
			}
		}
	}
}
</style>
