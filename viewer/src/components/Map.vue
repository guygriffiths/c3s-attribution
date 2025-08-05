<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import { onMounted, h, ref, Ref, watch } from 'vue'
import {
	LMap,
	LTileLayer,
	LControl,
	LControlScale,
	LControlZoom,
	LWmsTileLayer,
	LGridLayer,
	LPolygon,
	LGeoJson,
} from '@vue-leaflet/vue-leaflet'
import { LatLng, LatLngBounds, Point } from 'leaflet'
import { Map as LeafletMap } from 'leaflet'
import { T2M_LAYER, useStore, WMS_ROOT, catScheme } from '@/store/store'
import { debounce } from '@/lib/utils'
import { differenceInDays } from 'date-fns'
import scssVars from '@/assets/styles/scssVars.module.scss'
import FilterPanel from './FilterPanel.vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faFilter, faClose } from '@fortawesome/free-solid-svg-icons'
import L from 'leaflet'
import * as d3 from 'd3'

const store = useStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const eventHeatmapRef = ref<InstanceType<typeof LGridLayer> | null>(null)

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
			try {
				// TODO - 32px is hardcoded padding, yuck
				map.fitBounds(
					[
						[newVal.bbox[0], newVal.bbox[1]],
						[newVal.bbox[2], newVal.bbox[3]],
					],
					{
						paddingTopLeft: [64, 64],
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

watch(
	() => store.wrafRegion,
	(newVal) => {
		if (newVal === 'none') {
			store.regionsToSelectBy = undefined
		} else {
			fetch(`/regions/region-${newVal}.geojson`)
				.then((response) => response.json())
				.then((data: GeoJSON.FeatureCollection) => {
					store.regionsToSelectBy = data
					console.log('Regions to select by:', store.regionsToSelectBy)
				})
				.catch((error) => {
					console.error('Error fetching regions:', error)
				})
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

const getDataForTile = (coords: {
	x: number
	y: number
	z: number
}): number[][] => {
	const data = []
	for (let y = 0; y < 256; y++) {
		const row = []
		for (let x = 0; x < 256; x++) {
			row.push(Math.random()) // replace with real data
		}
		data.push(row)
	}
	return data
}

const getOpacity = (stepsFromNow: number) => {
	if (stepsFromNow === 0) {
		return 1
	}
	// const stepsFromNow = Math.abs(differenceInDays(store.selectedTime, store.selectedEvent.times[idx]))
	const maxSteps = 6
	const opacity = 0.5 - (0.5 * stepsFromNow) / maxSteps
	if (stepsFromNow > maxSteps) {
		return 0
	}
	return Math.max(opacity, 0.01)
}

watch(
	() => [store.selectedTime, store.selectedEvent],
	() => {
		if (eventHeatmapRef.value && eventHeatmapRef.value.leafletObject) {
			eventHeatmapRef.value.leafletObject.redraw()
		}
	},
)

// const tileGeometryCache = new Map()
const TILE_SIZE = 256
const LL_STEP = 0.25

const snap025 = (n: number) => Math.round(n * 4) / 4

const getTileGeometry = (
	coords: any,
	leafletObj: any,
) => {
	// const key = `${z}-${x}-${y}`
	// if (tileGeometryCache.has(key)) return tileGeometryCache.get(key)

	// const bounds = leafletObj._tileCoordsToBounds(coords)
	// console.log('getTileGeometry', coords, leafletObj)
	// TODO Cache this? I think it's more-or-less different for each event/tile combo. Not actually, but practically.
	const nwPoint = L.point(coords.x * TILE_SIZE, coords.y * TILE_SIZE);
	const sePoint = L.point((coords.x + 1) * TILE_SIZE, (coords.y + 1) * TILE_SIZE);

	const nw = leafletObj._map.unproject(nwPoint, coords.z);
	const se = leafletObj._map.unproject(sePoint, coords.z);

	const bounds =  L.latLngBounds(nw, se);
	const map = leafletObj._map
	const originX = coords.x * TILE_SIZE
	const originY = coords.y * TILE_SIZE
	const step = LL_STEP

	const latValues = []
	for (
		let lat = bounds.getSouth() - step;
		lat <= bounds.getNorth() + step;
		lat += step
	) {
		latValues.push(snap025(lat))
	}
	const lonValues = []
	for (
		let lon = bounds.getWest() - step;
		lon <= bounds.getEast() + step;
		lon += step
	) {
		lonValues.push(snap025(lon))
	}

	// Calculate consistent width/height for tiles
	const w = Math.ceil(
		map.project(L.latLng(latValues[0], lonValues[1]), coords.z).x -
			map.project(L.latLng(latValues[0], lonValues[0]), coords.z).x,
	)
	const h = Math.ceil(
		map.project(L.latLng(latValues[0], lonValues[0]), coords.z).y -
			map.project(L.latLng(latValues[1], lonValues[0]), coords.z).y,
	)
	const wAdjusted = w + 1
	const hAdjusted = h + 1

	const geometry = new Array(latValues.length * lonValues.length)
	let index = 0

	for (const lat of latValues) {
		for (const lon of lonValues) {
			const point = map.project(L.latLng(lat, lon), coords.z)
			const x = Math.floor(point.x - originX)
			const y = Math.floor(point.y - originY)
			// if (x < 0 || x > TILE_SIZE - 1 || y < 0 || y > TILE_SIZE - 1) {
			// 	geometry[index++] = null
			// } else {
			geometry[index++] = {
				x: x - Math.floor(wAdjusted / 2),
				y: y - Math.floor(hAdjusted / 2),
				w: wAdjusted,
				h: hAdjusted,
			}
			// }
		}
	}
	const latMap = new Map(latValues.map((v, i) => [v.toFixed(3), i]))
	const lonMap = new Map(lonValues.map((v, i) => [v.toFixed(3), i]))

	const geomFunc = (lat: number, lon: number) => {
		const latIndex = latMap.get(snap025(lat).toFixed(3))
		const lonIndex = lonMap.get(snap025(lon).toFixed(3))
		if (latIndex == null || lonIndex == null) return null
		return geometry[latIndex * lonValues.length + lonIndex]
	}

	// tileGeometryCache.set(key, geomFunc)
	return geomFunc
}

const getColor = (val: number) => {
	const cScale = d3.scaleLinear().domain([300, 320]).range([0, 1]).clamp(true)
	return d3.interpolateTurbo(cScale(val))
}

interface EventTileKey {
	coords: {
		x: number
		y: number
		z: number
	}
	t: number
	id: number
	key: string
}

const eventTileKey = (
	coords: { x: number; y: number; z: number },
	t: number,
	id: number,
): EventTileKey => ({
	coords,
	t,
	id,
	key: `${coords.x}-${coords.y}-${coords.z}-${t}-${id}`,
})

const tileImageCache = new Map<string, HTMLCanvasElement>()

const getCanvasFromCache = (key: EventTileKey) => {
	if (tileImageCache.has(key.key)) {
		// console.log('Cache hit for tile:', key.key)
		return tileImageCache.get(key.key)!
	}

	const canvas = document.createElement('canvas')
	canvas.width = TILE_SIZE
	canvas.height = TILE_SIZE
	const ctx = canvas.getContext('2d')
	if (!ctx) {
		console.error('Failed to get canvas context')
		return canvas
	}

	const layer = eventHeatmapRef.value
	if (layer?.leafletObject == undefined) {
		return canvas
	}

	const selectedIndex =
		differenceInDays(store.selectedTime, store.selectedEvent?.times[0]!) || 0
	const latLonValues = store.selectedEvent?.slices[selectedIndex] || []
	const dataValues = store.selectedEvent?.values[selectedIndex] || []

	const geometry = getTileGeometry(key.coords, layer.leafletObject)

	for (let i = 0; i < latLonValues.length; i++) {
		const latLon = latLonValues[i]
		const dataValue = dataValues[i]
		if (dataValue === undefined) continue

		const geom = geometry(latLon[0], latLon[1])
		if (!geom) continue

		const color = getColor(dataValue)
		ctx.fillStyle = color
		ctx.fillRect(geom.x, geom.y, geom.w, geom.h)
	}

	tileImageCache.set(key.key, canvas)

	return canvas
}

const drawEventTile = (props: any) => () => {
	const key = eventTileKey(
		props.coords,
		store.selectedEvent
			? differenceInDays(store.selectedTime, store.selectedEvent.times[0])
			: 0,
		store.selectedEvent?.id || 0,
	)

	const canvas = document.createElement('canvas')
	canvas.width = TILE_SIZE
	canvas.height = TILE_SIZE
	const ctx = canvas.getContext('2d')

	const tileCanvas = getCanvasFromCache(key)

	if (ctx !== null) {
		ctx.drawImage(tileCanvas, 0, 0)
	} else {
		console.error('Failed to get canvas context for event tile')
	}

	return h('canvas', {
		width: TILE_SIZE,
		height: TILE_SIZE,
		ref: (el) => {
			if (el && el !== canvas) {
				// @ts-ignore
				el.replaceWith(canvas)
			}
		},
	})
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
				:child-render="drawEventTile"
				pane="overlayPane"
			>
			</LGridLayer>
			<LGeoJson
				v-if="store.regionsToSelectBy"
				:geojson="store.regionsToSelectBy"
				:options-style="{
					// @ts-ignore
					className: 'region-select',
				}"
				class="region-select"
				@click="(e) => console.log('Region clicked', e)"
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
						? getOpacity(
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
				<select name="wraf-region" v-model="store.wrafRegion">
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
