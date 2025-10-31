<script lang="ts" setup>
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faDrawPolygon,
	faMapMarkerAlt,
	faBan,
	faPenAlt,
	faGlobe,
} from '@fortawesome/free-solid-svg-icons'
import { useLabels } from '@/lib/labels'
import scssModule from '@/assets/styles/scssVars.module.scss'
import { onFilterBuilt } from '@/lib/eventFiltering'
import { nextTick, ref } from 'vue'
import { IconMapPin, IconPencil, IconPolygon, IconWorld } from '@tabler/icons-vue'

const store = useStore()
const eventStore = useEventStore()
const $l = useLabels()

const ECMWF_BONN: [number, number] = [50.73438, 7.09549] // ECMWF location in Bonn
const setSelectingPoint = () => {
	if (store.filteringByPoint) {
		// Turn off point filtering and go back to global
		store.filteringByPoint = false
		store.regionFilterReady = false
		store.filteringByRegion = false
		return
	}
	store.setLoading() // start loading immediately
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

const ready = ref(false)
onFilterBuilt(() => {
	ready.value = true
})
</script>

<template>
	<div class="region-control">
		<div class="label">
			<IconPolygon size="16" aria-hidden="true" />
			<!-- <span>{{ $l.selectByRegion}}</span> -->
		</div>
		<!-- <p> {{ eventStore.eventPointFilter }}</p> -->

		<div>
			<button
				class="glassy"
				:class="{
					selected: store.exploreGlobal
				}"
				title="Explore global events"
				@click="setExploreGlobal"
			>
				<IconWorld class="icon" />
			</button>
			<button
				class="glassy"
				:class="{
					selected: store.filteringByRegion,
				}"
				title="Explore a region of your choice"
				:disabled="!ready"
				@click="setDrawingRegion"
			>
				<IconPencil class="icon" />
			</button>
			<button
				class="glassy"
				:class="{
					selected: store.filteringByPoint,
				}"
				:disabled="!ready"
				title="Explore events at a point"
				@click="setSelectingPoint"
			>
				<IconMapPin class="icon" />
			</button>
		</div>
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
	padding: 0;
	border-radius: 0.5rem;

	.label {
		font-weight: bolder;
		font-family: 'Raleway', sans-serif;
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
			transform: translate(-1px, 3px) scale(1.2);
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
}
</style>
