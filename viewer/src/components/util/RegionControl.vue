<script lang="ts" setup>
import { computed, nextTick, ref } from 'vue'
import { useStore } from '@/store/store'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faDrawPolygon,
	faTimes,
	faMapMarkerAlt,
	faClose,
	faBan,
	faPen,
	faPenAlt,
} from '@fortawesome/free-solid-svg-icons'
import * as d3 from 'd3'
import { useLabels } from '@/lib/labels'
import scssModule from '@/assets/styles/scssVars.module.scss'
import { LatLng } from 'leaflet'

const store = useStore()
const $l = useLabels()

const sizes: [
	number,
	string,
	'wraf-01' | 'wraf-05' | 'wraf-2' | 'wraf-5' | 'wraf-10',
][] = [
	[0.1, 'XS', 'wraf-01'],
	[0.5, 'S', 'wraf-05'],
	[2, 'M', 'wraf-2'],
	[5, 'L', 'wraf-5'],
	[10, 'XL', 'wraf-10'],
]
const selectedSize = computed(() => {
	if (store.wrafLevel === 'none') return null
	return sizes.findIndex((s) => s[2] === store.wrafLevel)
})

const selectSize = async (idx: number | null) => {
	if (idx !== null) {
		store.setLoading() // start loading immediately
	}
	store.wrafLevel = idx === null ? 'none' : sizes[idx][2]
	store.selectedPointFilter = null
	store.drawingRegion = false
	store.filters.wrafRegion = null
}
const ECMWF_BONN: [number, number] = [50.73438, 7.09549] // ECMWF location in Bonn
const setSelectingPoint = () => {
	// If we are already in this mode, turn it off
	if (store.selectedPointFilter !== null) {
		store.selectedPointFilter = null
		store.regionFilteredEvents = []
		store.runFilters()
		return
	}
	store.setLoading() // start loading immediately
	store.wrafLevel = 'none'
	store.drawingRegion = false
	store.filters.wrafRegion = null

	if(store.lastPoint) {
		store.selectedPointFilter = [store.lastPoint[0], store.lastPoint[1]]
	} else {
		store.selectedPointFilter = ECMWF_BONN
		if (navigator.geolocation) {
			navigator.geolocation.getCurrentPosition(
				(position) => {
					const { latitude, longitude } = position.coords
					store.selectedPointFilter = [latitude, longitude]
				},
				() => {
					console.warn('Unable to retrieve your location. Using ECMWF location.')
					store.selectedPointFilter = ECMWF_BONN
				},
			)
		}
	}

	store.getPointFilteredEvents(store.selectedPointFilter[0], store.selectedPointFilter[1])
	store.fixPointFilteredEvents()
}

const drawRegion = () => {
	store.wrafLevel = 'none'
	store.selectedPointFilter = null
	store.filters.wrafRegion = null
	store.regionFilteredEvents = []
	store.drawingRegion = !store.drawingRegion
	if(store.drawingRegion) {
		// TODO - this should be set in the store anyway. We should watch it, then set the full filter going on a worker thread. That way we can pre-calc a bunch of simplified regions for events (but *larger* - must fully encapsulate total_region) throw them through the fast filter, and use the exact filter in the background. And by *full*, we can do a proper check of every pixel's inclusion (which we have
		// store.regionFilteredEvents = []
	}


}

const sizeScheme = d3.interpolateWarm
</script>

<template>
	<div class="region-control">
		<div class="label">
			<FontAwesomeIcon :icon="faDrawPolygon" />
			<!-- <span>{{ $l.selectByRegion}}</span> -->
		</div>
		<!-- <p> {{ store.selectedPointFilter }}</p> -->

		<div>
			<button
				class="none-button"
				:class="{
					selected:
						selectedSize === null &&
						store.selectedPointFilter === null &&
						store.filters.wrafRegion === null,
				}"
				title="None"
				@click="selectSize(null)"
			>
				<FontAwesomeIcon :icon="faBan" />
			</button>

			<template v-for="(size, i) in sizes" :key="size">
				<button
					:style="{
						backgroundColor: sizeScheme(i / 5),
						color: selectedSize === i ? sizeScheme(i / 5) : 'white',
					}"
					:title="`${size[0]} Mm²`"
					:class="{ selected: selectedSize === i }"
					@click="selectSize(i)"
				>
					{{ size[1] }}
				</button>
			</template>

			<button
				:style="{ backgroundColor: scssModule.c3sred }"
				:class="{
					selected:
						store.drawingRegion,
				}"
				title="Point"
				@click="drawRegion"
			>
				<FontAwesomeIcon :icon="faPenAlt" />
			</button>
			<button
				:style="{ backgroundColor: scssModule.c3sred }"
				:class="{
					selected: selectedSize === null && store.selectedPointFilter !== null,
				}"
				title="Point"
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

		&.none-button {
			background-color: rgb(64, 64, 64);
			&.selected {
				color: rgb(64, 64, 64);
				svg {
					color: rgb(64, 64, 64) !important;
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
