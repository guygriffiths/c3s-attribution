<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import { ref, Ref, watch } from 'vue'
import {
	LMap,
	LTileLayer,
	LControl,
	LControlScale,
	LControlZoom,
	LGridLayer,
	LPolygon,
	LGeoJson,
} from '@vue-leaflet/vue-leaflet'
import { LatLng, LatLngBounds, Point } from 'leaflet'
import { Map as LeafletMap } from 'leaflet'
import { T2M_LAYER, useStore, WMS_ROOT, catScheme } from '@/store/store'
import { debounce } from '@/lib/utils'
import { differenceInDays } from 'date-fns'

import FilterPanel from './FilterPanel.vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faFilter, faClose } from '@fortawesome/free-solid-svg-icons'
import { drawEventTile, TILE_SIZE } from '@/lib/renderer'
import { Feature, MultiPolygon, Polygon } from 'geojson'
import {
	fitMapToBounds,
	wrafLevelChanged,
	getZeitgeistOpacity,
} from '@/lib/map-utils'
import { bbox } from '@turf/turf'

const store = useStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const eventHeatmapRef = ref<InstanceType<typeof LGridLayer> | null>(null)

const mapOptions = {
	zoomControl: false,
	zoomSnap: 1,
	zoomDelta: 1,
	wheelPxPerZoomLevel: 240,
	fadeAnimation: false
}
const centerPoint: Ref<Point> = ref(new LatLng(0, 0) as unknown as Point)
const zoom = ref(3)

const bgLayer = {
	name: 'Stadia OSM Bright',
	url: 'https://tiles.stadiamaps.com/tiles/osm_bright/{z}/{x}/{y}{r}.png',
	attribution:
		'&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
}

const wmtsUrl = ref(
	`https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${store.isoDatetime}`,
)

watch(
	() => store.isoDatetime,
	() => {
		debounce(() => {
			console.warn('Do not forget to recomment this')
			// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
		}, 500)
	},
)

watch(
	() => store.selectedEvent,
	(newVal) => {
		if (newVal && mapRef.value) {
			const map: LeafletMap = mapRef.value.leafletObject as LeafletMap
			fitMapToBounds(map, newVal)
		}
	},
)

watch( () => store.filters.wrafRegion,
	(newVal) => {
		if (newVal && mapRef.value) {
			const map: LeafletMap = mapRef.value.leafletObject as LeafletMap
			const bounds = bbox(store.filters.wrafRegion)	
			console.log('need to find bbox of region', bounds)
			map.fitBounds([
				[bounds[1], bounds[0]],
				[bounds[3], bounds[2]],
			])
		}
	},
)

watch(
	() => store.wrafLevel,
	(newVal) => {
		wrafLevelChanged(store, newVal || 'none')
	},
)

const selectRegion = (event: any) => {
	if (event.layer && event.layer.feature) {
		const region = event.layer.feature as Feature<Polygon | MultiPolygon>
		store.filters.wrafRegion = region
		console.log('Selected region:', region)

	} else {
		console.warn('No layer or feature found in click event:', event)
	}
}

const getEventRegion = (event: any) => {
	const idx = event.times.findIndex(
		(t: Date) =>
			new Date(t).getTime() === new Date(store.selectedTime).getTime(),
	)
	if (idx < 0) {
		return event.regions[0] || [] // Fallback to first region if no matching time found
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

watch(
	() => [store.selectedTime, store.selectedEvent],
	() => {
		if (eventHeatmapRef.value && eventHeatmapRef.value.leafletObject) {
			eventHeatmapRef.value.leafletObject.redraw()
		}
	},
)

const renderTile = (props: any) =>
	drawEventTile(props, store, eventHeatmapRef.value)
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

			<LTileLayer
				class="bg-map"
				:url="wmtsUrl"
				:zIndex="2"
				:opacity="0.75"
			></LTileLayer>
			<LGridLayer
				ref="eventHeatmapRef"
				class="event-heatmap"
				:tileSize="TILE_SIZE"
				:child-render="renderTile"
				:options="{
					fadeAnimation: false,
				}"
				pane="overlayPane"
			>
			</LGridLayer>
			<LGeoJson
				v-if="store.regionsToSelectBy && !store.filters.wrafRegion"
				:geojson="store.regionsToSelectBy"
				:options-style="() => ({
					// @ts-ignore
					className: 'region-select',
				})"
				class="region-select"
				@click="selectRegion"
			>
			</LGeoJson>
			<LGeoJson
				v-if="store.filters.wrafRegion"
				:geojson="store.filters.wrafRegion"
				:options-style="() => ({
					// @ts-ignore
					className: 'region-select',
				})"
				class="region-select"
				@click="selectRegion"
			>
			</LGeoJson>
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
			</LPolygon>
			<LPolygon
				v-for="(region, idx) in store.selectedEvent?.regions"
				:key="idx"
				:lat-lngs="region"
				:weight="1"
				:fill="false"
				:opacity="
					store.selectedEvent
						? getZeitgeistOpacity(
								Math.abs(
									differenceInDays(
										store.selectedTime,
										store.selectedEvent.times[idx],
									),
								),
							)
						: 0
				"
				:color="catScheme[store.selectedEvent?.id! % catScheme.length]"
				@click="selectEvent(store.selectedEvent?.id!)"
			>
			</LPolygon>
			<LControl position="topright" class="filter-container">
				<button @click="store.filtersExpanded = !store.filtersExpanded">
					<FontAwesomeIcon :icon="store.filtersExpanded ? faClose : faFilter" />
				</button>
				<FilterPanel
					v-show="store.filtersExpanded"
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
							key: 'includeOceanEvents',
							label: 'Include ocean-only events',
							type: 'toggle',
						},
					]"
					@drag-start="store.draggingFilter = true"
					@drag-end="store.draggingFilter = false"
				/>
				<!-- <div>
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
				</div> -->
			</LControl>
			<LControl
				:max-width="200"
				:metric="true"
				:imperial="false"
				position="topleft"
				class="map-scale"
			>
				<select name="wraf-region" v-model="store.wrafLevel">
					<option value="none">None</option>
					<option value="wraf-01">WRAF 0.1 Mm²</option>
					<option value="wraf-05">WRAF 0.5 Mm²</option>
					<option value="wraf-2">WRAF 2 Mm²</option>
					<option value="wraf-5">WRAF 5 Mm²</option>
					<option value="wraf-10">WRAF 10 Mm²</option>
				</select></LControl
			>
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

	.filter-container {
		position: relative;
		button {
			position: absolute;
			top: 0;
			right: 0;
			z-index: 100;
			background-color: $bgContrast;
			color: $textColor;
			border: none;
			padding: 0.5rem 1rem;
			cursor: pointer;
			transition: background-color $animTime ease-in-out;
			&:hover {
				background-color: $bg;
			}
		}
	}

	.filter-panel {
		padding: 1rem;
	}

	:deep(.region-select) {
		stroke: rgb(0.25, 0.25, 0.25);
		stroke-width: 1px;
		fill: rgba(0, 0, 0, 0.4);
		cursor: pointer;
		&:hover {
			fill: rgba(0, 0, 0, 0.5);
			stroke-width: 2px;
		}
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
