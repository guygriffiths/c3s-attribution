<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import { computed, ref, Ref, watch } from 'vue'
import {
	LMap,
	LTileLayer,
	LControl,
	LControlScale,
	LControlZoom,
	LWmsTileLayer,
	LCircleMarker,
	LPopup,
	LPolygon,
} from '@vue-leaflet/vue-leaflet'
import { LatLng, Map, Point } from 'leaflet'
import { T2M_LAYER, useStore, WMS_ROOT } from '@/store/store'
import { differenceInDays } from 'date-fns'
import { schemeCategory10 } from 'd3'

const store = useStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const wmsRef = ref<InstanceType<typeof LWmsTileLayer> | null>(null)

const mapOptions = {
	zoomControl: false,
	zoomSnap: 1,
	zoomDelta: 1,
	wheelPxPerZoomLevel: 240,
}
const centerPoint: Ref<Point> = ref(new LatLng(30, 0) as unknown as Point)
const zoom = ref(2)

const bgLayer = {
	name: 'Stadia OSM Bright',
	url: 'https://tiles.stadiamaps.com/tiles/osm_bright/{z}/{x}/{y}{r}.png',
	attribution:
		'&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
}

// TODO Can we add a delay before this gets updated? We probably want to use another variable, watch store.isoDatetime, and set a timeout.
// OR convert to a ref instead, and use a watcher on store.isoDatetime to update the ref.
const wmtsUrl = ref(
	`https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${store.isoDatetime}`,
)

let debounceTimeout: NodeJS.Timeout | null = null
const debounce = (func: () => void, delay: number) => {
	if (debounceTimeout) {
		clearTimeout(debounceTimeout)
	}
	debounceTimeout = setTimeout(() => {
		func()
	}, delay)
}
watch(
	() => store.isoDatetime,
	(newVal) => {
		debounce(() => {
			console.warn('Do not forget to uncomment this')
			// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
		}, 500)
	},
)

const getEventRegion = (event: any) => {
	const idx = event.times.findIndex(
		(t: Date) =>
			new Date(t).getTime() === new Date(store.selectedTime).getTime(),
	)
	if (idx < 0) {
		return []
	}

	return event.regions[idx]
}
</script>

<template>
	<div class="map">
		<LMap
			ref="mapRef"
			v-model:zoom="zoom"
			:center="centerPoint"
			:max-zoom="12"
			:min-zoom="1"
			:options="mapOptions"
			style="z-index: 1"
			:zoom-animation="true"
			@ready=""
		>
			<LTileLayer
				:url="bgLayer.url"
				:attribution="bgLayer.attribution"
				layer-type="base"
				:zIndex="1"
			></LTileLayer>
			<LTileLayer :url="wmtsUrl" :zIndex="2" :opacity="0.75"></LTileLayer>
			<!-- TODO Find out why these don't look like the centroid... -->
			<!-- <div v-for="(event, idx) in store.activeEvents">
				<LCircleMarker
					v-for="point in event.slices[
						event.times.findIndex(
							(t) =>
								new Date(t).getTime() ===
								new Date(store.selectedTime).getTime(),
						)
					]"
					:lat-lng="point"
					:radius="2"
					:color="schemeCategory10[event.id % 10]"
				>
				</LCircleMarker>
			</div> -->
			<LPolygon
				v-for="(event, idx) in store.activeEvents"
				:lat-lngs="getEventRegion(event)"
				:weight="2"
				:fill="false"
				:opacity="0.5"
				:color="schemeCategory10[idx % 10]"
			>
				<LPopup>
					<p>{{ event }}</p>
				</LPopup>
			</LPolygon>
			<LControl position="bottomleft">
				<div>
					<p>
						{{ store.selectedTime }}
					</p>
				</div>
			</LControl>
			<LControlScale
				:max-width="200"
				:metric="true"
				:imperial="false"
				position="bottomright"
				class="map-scale"
			></LControlScale>
			<LControlZoom></LControlZoom>
		</LMap>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.scss' as *;

.map {
	width: 100%;
	height: 100%;

	:deep(.leaflet-control-zoom),
	:deep(.leaflet-control-zoom-out),
	:deep(.leaflet-control-zoom-in) {
		background-color: $bg;
		border-color: $bgContrast;
	}
}
</style>
