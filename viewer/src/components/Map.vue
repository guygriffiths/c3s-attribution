<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import { onMounted, ref, Ref, watch } from 'vue'
import {
	LMap,
	LTileLayer,
	LControl,
	LControlScale,
	LControlZoom,
	LWmsTileLayer,
} from '@vue-leaflet/vue-leaflet'
import { LatLng, Map, Point } from 'leaflet'
import { T2M_LAYER, useStore, WMS_ROOT } from '@/store/store'

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

watch(
	() => store.isoDatetime,
	(newTime) => {
		if (newTime) {
			console.log('newTime', newTime, 'wmsRef', wmsRef.value)
			wmsRef.value?.leafletObject?.setParams({
				// @ts-ignore
				time: newTime,
			})
		}
	},
)
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
			<!-- url="https://era-explorer.ecmwf-development.f.ewcloud.host/geoserver/wms" -->
			<LWmsTileLayer
				ref="wmsRef"
				v-show="store.selectedTime"
				:url="WMS_ROOT"
				:layers="T2M_LAYER"
				format="image/png"
				styles="default"
				layer-type="base"
				:options="{
					time: store.isoDatetime,
				}"
				:zIndex="2"
				:opacity="0.75"
			></LWmsTileLayer>
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
