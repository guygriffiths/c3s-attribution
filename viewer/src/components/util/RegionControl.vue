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

const store = useStore()
const eventStore = useEventStore()
const $l = useLabels()

const ECMWF_BONN: [number, number] = [50.73438, 7.09549] // ECMWF location in Bonn
const setSelectingPoint = () => {
	console.log('setSelectingPoint')
	if (store.filteringByPoint) {
		// Cancel selecting point
		store.filteringByPoint = false
		store.exploreGlobal = false
		store.regionFilterReady = false
		store.filteringByRegion = false
		return
	}
	console.log('Not already filtering by point')
	store.setLoading() // start loading immediately
	console.log('Set loading')
	store.filteringByPoint = true
	console.log('Set filtering by point')
	store.exploreGlobal = false
	console.log('Set not exploring globally')
	store.regionFilterReady = false
	console.log('Set region filter not ready')
	store.filteringByRegion = false
	console.log('Set region filtering off')
}

const setDrawingRegion = () => {
	if (store.filteringByRegion) {
		// Cancel drawing
		store.filteringByRegion = false
		store.regionFilterReady = false
		store.exploreGlobal = false
		store.filteringByPoint = false
		return
	} else {
		store.filteringByRegion = true
		store.regionFilterReady = false
		store.filteringByPoint = false
		store.exploreGlobal = false
	}
}

const setExploreGlobal = () => {
	if (store.exploreGlobal) {
		// Cancel exploring global
		store.exploreGlobal = false
		store.filteringByPoint = false
		store.regionFilterReady = false
		store.filteringByRegion = false
		return
	}
	store.exploreGlobal = true
	store.filteringByPoint = false
	store.regionFilterReady = false
	store.filteringByRegion = false
}

const noExplore = () => {
	store.regionFilterReady = false
	store.filteringByRegion = false
	store.filteringByPoint = false
	store.exploreGlobal = false
}

const ready = ref(false)
onFilterBuilt(() => {
	ready.value = true
})
</script>

<template>
	<div class="region-control">
		<div class="label">
			<FontAwesomeIcon :icon="faDrawPolygon" />
			<!-- <span>{{ $l.selectByRegion}}</span> -->
		</div>
		<!-- <p> {{ eventStore.eventPointFilter }}</p> -->

		<div>
			<button
				class="none-button"
				:class="{
					selected:
						store.filteringByPoint === false &&
						store.filteringByRegion === false &&
						store.exploreGlobal === false,
				}"
				:style="{ backgroundColor: scssModule.c3sred }"
				title="No event charts, just view the global heatmap"
				@click="noExplore"
			>
				<FontAwesomeIcon :icon="faBan" />
			</button>

			<button
				:style="{ backgroundColor: scssModule.c3sred }"
				:class="{
					selected: store.exploreGlobal,
				}"
				title="Explore global events"
				@click="setExploreGlobal"
			>
				<FontAwesomeIcon :icon="faGlobe" />
			</button>
			<button
				:style="{ backgroundColor: scssModule.c3sred }"
				:class="{
					selected: store.filteringByRegion,
				}"
				title="Explore a region of your choice"
				:disabled="!ready"
				@click="setDrawingRegion"
			>
				<FontAwesomeIcon :icon="faPenAlt" />
			</button>
			<button
				:style="{ backgroundColor: scssModule.c3sred }"
				:class="{
					selected: store.filteringByPoint,
				}"
				:disabled="!ready"
				title="Explore events at a point"
				@click="setSelectingPoint"
			>
				<FontAwesomeIcon :icon="faMapMarkerAlt" />
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
	background-color: rgba($c3sblue, 0.33);
	padding: 0;
	border-radius: 0.5rem;

	.label {
		font-weight: bolder;
		font-family: 'Raleway', sans-serif;
		font-size: 1rem;
		position: absolute;
		top: -0.75rem;
		left: -0.75rem;
		background-color: rgba(255, 255, 255, 0.9);
		border-radius: 100%;
		padding: 0 0.3rem;
		border: 1px solid rgba(0, 0, 0, 0.2);
	}

	button {
		margin: 0 0.05rem;
		font-family: 'Raleway', sans-serif;
		font-weight: bolder;
		color: rgb(255, 255, 255);

		&:disabled {
			opacity: 0.5;
			cursor: not-allowed;
		}

		&.none-button {
			// background-color: rgb(64, 64, 64);
			&.selected {
				// color: rgb(64, 64, 64);
				svg {
					// color: rgb(64, 64, 64) !important;
					filter: drop-shadow(0 0 1px rgb(255, 255, 255))
						drop-shadow(0 0 2px rgb(255, 255, 255))
						drop-shadow(0 0 5px rgb(255, 255, 255))
						drop-shadow(0 0 10px rgb(255, 255, 255));
				}
			}
		}
	}
}
</style>
