<script lang="ts" setup>
import { useStore } from '@/store/store'
import {
	IconLayersSelected,
	IconMapPin,
	IconPolygon,
	IconWorld,
} from '@tabler/icons-vue'
import { ref } from 'vue'
import { useLabels } from '@/lib/labels'

const $l = useLabels()

const store = useStore()

const setSelectingPoint = () => {
	if (store.filteringByPoint) {
		// Turn off point filtering and go back to global
		store.filteringByPoint = false
		store.regionFilterReady = false
		store.filteringByRegion = false
		return
	}
	store.filteringByPoint = true
	store.regionFilterReady = false
	store.filteringByRegion = false
}

const setDrawingRegion = () => {
	if (store.filteringByRegion) {
		// Cancel drawing
		store.filteringByRegion = false
		store.regionFilterReady = false
		store.filteringByPoint = false
		// Set back to global
	} else {
		store.filteringByRegion = true
		store.regionFilterReady = false
		store.filteringByPoint = false
	}
}

const setExploreGlobal = () => {
	// Don't toggle this, there's nothing to unset
	store.filteringByPoint = false
	store.regionFilterReady = false
	store.filteringByRegion = false
}

const ready = ref(true)
// onFilterBuilt(() => {
// 	ready.value = true
// })
</script>

<template>
	<div class="region-control">
		<div class="label">
			<IconLayersSelected size="16" aria-hidden="true" />
			<!-- <span>{{ $l.selectByRegion}}</span> -->
		</div>
		<!-- <p> {{ eventStore.eventPointFilter }}</p> -->

		<div>
			<button
				class="glassy"
				:class="{
					selected: store.exploreGlobal,
				}"
				:aria-pressed="store.exploreGlobal"
				@click="setExploreGlobal"
				v-tooltip="$l.exploreGlobal"
			>
				<IconWorld class="icon" aria-hidden="true" />
			</button>
			<button
				class="glassy"
				:class="{
					selected: store.filteringByRegion,
				}"
				:aria-pressed="store.filteringByRegion"
				:disabled="!ready"
				@click="setDrawingRegion"
				v-tooltip="$l.selectByRegion"
			>
				<IconPolygon class="icon" aria-hidden="true" />
			</button>
			<button
				class="glassy"
				:class="{
					selected: store.filteringByPoint,
				}"
				:aria-pressed="store.filteringByPoint"
				:disabled="!ready"
				@click="setSelectingPoint"
				v-tooltip="$l.selectByPoint"
			>
				<IconMapPin class="icon" aria-hidden="true" />
			</button>
		</div>
		<slot />
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.region-control {
	display: flex;
	flex-direction: column;
	gap: 0;
	position: relative;
	margin-top: 0.75rem;
	margin-left: 0.25rem;
	padding: 0 2rem 2rem 0;
	border-radius: 0.5rem;
	// background-color: aqua;

	.label {
		font-weight: bolder;
		font-size: 1rem;
		position: absolute;
		top: -0.75rem;
		left: -0.75rem;
		background-color: var(--panel-bg);
		backdrop-filter: $frosty;
		border-radius: 100%;
		padding: 0 0.3rem;
		border: 1px solid rgba(0, 0, 0, 0.2);
		z-index: 10;

		svg {
			transform: translate(0, 3px) scale(1.2);
		}
	}

	button {
		margin: 0;
		border-radius: 0;

		&:first-child {
			border-top-left-radius: $borderRadius;
			border-bottom-left-radius: $borderRadius;
		}
		&:last-child {
			border-top-right-radius: $borderRadius;
			border-bottom-right-radius: $borderRadius;
		}
	}

	:deep(.help-button) {
		opacity: 0;
		pointer-events: none;
		transition: opacity $animTime $animEase;
	}

	&:hover,
	&:focus {
		:deep(.help-button) {
			opacity: 1;
			pointer-events: all;
		}
	}
}
</style>
