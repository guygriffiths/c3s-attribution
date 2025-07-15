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
	LMarker,
	LPopup,
	LPolygon,
} from '@vue-leaflet/vue-leaflet'
import { LatLng, LatLngBounds, Map, Point, icon } from 'leaflet'
import { T2M_LAYER, useStore, WMS_ROOT, catScheme } from '@/store/store'
import { debounce } from '@/lib/utils'
import markerIconImg from '@/assets/img/marker-icon-2x-c3sred.png'
import gridpointIconImg from '@/assets/img/gridpoint-icon.png'
import { differenceInDays } from 'date-fns'
import scssVars from '@/assets/styles/scssVars.module.scss'
import FilterPanel from './FilterPanel.vue'

const store = useStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const wmsRef = ref<InstanceType<typeof LWmsTileLayer> | null>(null)

const mapOptions = {
	zoomControl: false,
	zoomSnap: 1,
	zoomDelta: 1,
	wheelPxPerZoomLevel: 240,
}
const centerPoint: Ref<Point> = ref(new LatLng(0, 0) as unknown as Point)
const zoom = ref(3)

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

watch(
	() => store.isoDatetime,
	(newVal) => {
		debounce(() => {
			console.warn('Do not forget to uncomment this')
			// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
		}, 500)
	},
)

watch(
	() => store.selectedEvent,
	(newVal) => {
		if (newVal && mapRef.value) {
			const map: Map = mapRef.value.leafletObject as Map
			// console.log('fitting bounds', newVal.bbox, newVal.regions)
			try {
				// TODO - 32px is hardcoded padding, yuck
				map.fitBounds(
					[
						[newVal.bbox[0], newVal.bbox[1]],
						[newVal.bbox[2], newVal.bbox[3]],
					],
					{
						paddingTopLeft: [32, 32],
						paddingBottomRight: [
							map.getSize().x * 0.5 + 32,
							map.getSize().y * 0.5 + 32,
						],
						maxZoom: 12,
						// @ts-ignore
						duration: scssVars.animTime,
					},
				)
			} catch (e) {
				console.error('Error fitting bounds:', e)
			}
		}
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
	return event.regions[idx] || [] // Fallback to empty array if no region found
}

const lastBbox = ref<LatLngBounds | null>(null)
const selectEvent = (id: number) => {
	if (!store.eventSelected) {
		// @ts-ignore
		lastBbox.value = mapRef.value?.leafletObject.getBounds()
	} else if (id == store.selectedEvent?.id) {
		if (lastBbox.value && mapRef.value) {
			// @ts-ignore
			mapRef.value.leafletObject.fitBounds(lastBbox.value)
		}
	}
	store.selectEvent(id)
}

const markerIcon = icon({
	iconUrl: markerIconImg, // or a URL string
	iconSize: [25, 41], // width and height
	iconAnchor: [13, 41], // point of the icon which will correspond to marker's location
	popupAnchor: [0, -41], // point from which the popup should open
})
const gridpointIcon = icon({
	iconUrl: gridpointIconImg, // or a URL string
	iconSize: [7, 7], // width and height
	iconAnchor: [4, 4], // point of the icon which will correspond to marker's location
	popupAnchor: [4, 4], // point from which the popup should open
})
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

			<!-- <l-marker :lat-lng="[51.437576, -0.941099]" :icon="markerIcon" /> -->
			<LTileLayer :url="wmtsUrl" :zIndex="2" :opacity="0.75"></LTileLayer>
			<LMarker
				v-for="point in store.selectedEvent?.slices[
					differenceInDays(store.selectedTime, store.selectedEvent?.times[0]) ||
						0
				]"
				:lat-lng="point"
				:icon="gridpointIcon"
			>
			</LMarker>
			<LPolygon
				v-for="(event, idx) in store.currentEvents"
				:key="event.id"
				:lat-lngs="getEventRegion(event)"
				:weight="3"
				:fill="true"
				:opacity="1"
				:color="catScheme[event.id % catScheme.length]"
				@click="selectEvent(event.id)"
			>
				<!-- <LPopup>
					<p>{{ event }}</p>
				</LPopup> -->
			</LPolygon>
			<LControl position="topright">
				<FilterPanel
					v-model="store.filters"
					class="filter panel"
					:filters="[
						{
							key: 'duration',
							label: 'Duration (days)',
							type: 'range',
							pass: 'high-pass',
							min: 3,
							max: 14,
						},
						{
							key: 'intensity',
							label: 'Intensity %ile',
							type: 'range',
							pass: 'high-pass',
							min: 0,
							max: 99,
						},
						{
							key: 'size',
							label: 'Size %ile',
							type: 'range',
							pass: 'high-pass',
							min: 0,
							max: 99,
						},
						{
							key: 'includeOceanOnly',
							label: 'Include ocean-only events',
							type: 'toggle',
						},
					]"
					@drag-start="store.draggingFilter = true"
					@drag-end="store.draggingFilter = false"
				/>
				<div>
					<p>
						{{ store.isoDatetime }}
						{{ store.filters }}
					</p>
					<select
						v-model="store.selectedModel"
						@change="store.init()"
						class="form-select form-select-sm"
					>
						<option value="RAD5-DBSCANFalse-THRESH301.15-PERC98" selected>
							RAD5-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD6-DBSCANFalse-THRESH301.15-PERC98">
							RAD6-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD7-DBSCANFalse-THRESH301.15-PERC98">
							RAD7-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD4-DBSCANFalse-THRESH301.15-PERC98">
							RAD4-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD3-DBSCANFalse-THRESH301.15-PERC98">
							RAD3-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD2-DBSCANFalse-THRESH301.15-PERC98">
							RAD2-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD1-DBSCANFalse-THRESH301.15-PERC98">
							RAD1-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD8-DBSCANFalse-THRESH301.15-PERC98">
							RAD8-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD9-DBSCANFalse-THRESH301.15-PERC98">
							RAD9-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD10-DBSCANFalse-THRESH301.15-PERC98">
							RAD10-DBSCANFalse-THRESH301.15-PERC98
						</option>
						<option value="RAD5-DBSCANFalse-THRESH303.15-PERC98">
							RAD5-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD6-DBSCANFalse-THRESH303.15-PERC98">
							RAD6-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD7-DBSCANFalse-THRESH303.15-PERC98">
							RAD7-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD4-DBSCANFalse-THRESH303.15-PERC98">
							RAD4-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD3-DBSCANFalse-THRESH303.15-PERC98">
							RAD3-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD2-DBSCANFalse-THRESH303.15-PERC98">
							RAD2-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD1-DBSCANFalse-THRESH303.15-PERC98">
							RAD1-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD8-DBSCANFalse-THRESH303.15-PERC98">
							RAD8-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD9-DBSCANFalse-THRESH303.15-PERC98">
							RAD9-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD10-DBSCANFalse-THRESH303.15-PERC98">
							RAD10-DBSCANFalse-THRESH303.15-PERC98
						</option>
						<option value="RAD5-DBSCANFalse-THRESH305.15-PERC98">
							RAD5-DBSCANFalse-THRESH305.15-PERC98
						</option>
						<option value="RAD6-DBSCANFalse-THRESH305.15-PERC98">
							RAD6-DBSCANFalse-THRESH305.15-PERC98
						</option>
						<option value="RAD7-DBSCANFalse-THRESH305.15-PERC98">
							RAD7-DBSCANFalse-THRESH305.15-PERC98
						</option>
						<option value="RAD4-DBSCANFalse-THRESH305.15-PERC98">
							RAD4-DBSCANFalse-THRESH305.15-PERC98
						</option>
						<option value="RAD3-DBSCANFalse-THRESH305.15-PERC98">
							RAD3-DBSCANFalse-THRESH305.15-PERC98
						</option>
					</select>
				</div>
			</LControl>
			<LControlScale
				:max-width="200"
				:metric="true"
				:imperial="false"
				position="bottomright"
				class="map-scale"
			></LControlScale>
			<LControlZoom :class="{ shifted: store.eventSelected }"></LControlZoom>
		</LMap>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.map {
	width: 100%;
	height: 100%;

	.filter-panel {
		// padding: 1rem;
	}

	:deep(.leaflet-control-zoom),
	:deep(.leaflet-control-zoom-out),
	:deep(.leaflet-control-zoom-in) {
		background-color: $bg;
		border-color: $bgContrast;
	}

	:deep(.leaflet-tile) {
		image-rendering: pixelated; /* or auto/smooth depending on your preference */
		transform-origin: center center;
	}
}
</style>
