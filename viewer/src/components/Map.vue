<script setup lang="ts">
import { debounce } from '@/lib/utils'
import { useStore } from '@/store/store'
import {
	LControl,
	LControlScale,
	LGeoJson,
	LGridLayer,
	LMap,
	LMarker,
	LPolygon,
	LTileLayer,
} from '@vue-leaflet/vue-leaflet'
import { differenceInDays } from 'date-fns'
import { LatLngBounds, Map as LeafletMap, LeafletMouseEvent } from 'leaflet'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet/dist/leaflet.css'
import { computed, nextTick, ref, watch } from 'vue'

import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	fitMapToBounds,
	getZeitgeistOpacity,
	markerIcon,
	wrafLevelChanged,
} from '@/lib/map-utils'
import { drawEventTile, TILE_SIZE } from '@/lib/renderer'
import { faClose, faFilter } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { bbox, featureCollection, polygon } from '@turf/turf'
import { Feature, MultiPolygon, Polygon } from 'geojson'
import FilterPanel from './FilterPanel.vue'
import RegionControl from './util/RegionControl.vue'
const { vTimePanelWidth, panelMargin, frameBorderWidth } = scssVars

const store = useStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const map = computed(() => mapRef.value?.leafletObject as LeafletMap)
const eventPixelsRef = ref<InstanceType<typeof LGridLayer> | null>(null)

const currentEvents = computed(() => {
	if (store.filters.wrafRegion) {
		return store.filteredEvents
	}
	return store.currentEvents
})

import L from 'leaflet'
import ModeToggle from './util/ModeToggle.vue'
// create a single canvas renderer for all polygons
const canvasRenderer = L.canvas({ padding: 0.5, pane: 'eventPane' })
const fastRenderer = L.canvas({ padding: 0.5, pane: 'fastEventPane' })

const mapOptions = {
	zoomControl: false,
	zoomSnap: 1,
	zoomDelta: 1,
	wheelPxPerZoomLevel: 240,
	fadeAnimation: false,
}

const zoom = ref(2)

const bgLayer = {
	name: 'Stadia OSM Bright',
	url: 'https://tiles.stadiamaps.com/tiles/osm_bright/{z}/{x}/{y}{r}.png',
	attribution:
		'&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
}

const wmtsUrl = ref(
	`https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${store.isoDatetime}`,
)
const updateWmtsUrl = debounce((newVal: string) => {
	console.log(
		'Updating WMTS URL to:',
		newVal,
		' (nah, not really. You should probably uncomment the next line at some point)',
	)
	// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
}, 500)
watch(() => store.isoDatetime, updateWmtsUrl)

watch(
	() => store.selectedEvent,
	(newVal) => {
		const id = newVal?.id
		if (!store.eventSelected) {
			// @ts-ignore
			lastBbox.value = mapRef.value?.leafletObject.getBounds()
		} else if (store.selectedEvent?.id == id) {
			if (lastBbox.value && mapRef.value) {
				// @ts-ignore
				mapRef.value.leafletObject.fitBounds(lastBbox.value)
			}
		}
		if (id && mapRef.value) {
			const map: LeafletMap = mapRef.value.leafletObject as LeafletMap
			fitMapToBounds(map, store.selectedEvent!)
		}
	},
)

const multiEventsSelected = () => {
	lastBbox.value = map.value.getBounds()

	const bounds = bbox(
		store.filters.wrafRegion ||
			featureCollection(
				store.currentEvents.map((e) => polygon([e.total_region])),
			),
	)

	function toPx(value: string): number {
		if (value.endsWith('%')) {
			return (window.innerWidth * parseFloat(value)) / 100
		}
		if (value.endsWith('rem')) {
			return (
				parseFloat(value) *
				parseFloat(getComputedStyle(document.documentElement).fontSize)
			)
		}
		if (value.endsWith('px')) {
			return parseFloat(value)
		}
		return parseFloat(value) // fallback
	}

	const peepholeWidth =
		window.innerWidth -
		toPx(vTimePanelWidth) -
		2 * toPx(panelMargin) -
		2 * toPx(frameBorderWidth)

	const peepholeHeight = window.innerHeight / 2 - toPx(frameBorderWidth)

	const padLeft =
		toPx(panelMargin) + toPx(vTimePanelWidth) + toPx(frameBorderWidth)
	const padTop = toPx(panelMargin) + toPx(frameBorderWidth)
	const padRight = window.innerWidth - (padLeft + peepholeWidth)
	const padBottom = window.innerHeight - (padTop + peepholeHeight)

	map.value.fitBounds(
		[
			[bounds[1], bounds[0]],
			[bounds[3], bounds[2]],
		],
		{
			paddingTopLeft: [padLeft, padTop],
			paddingBottomRight: [padRight, padBottom],
		},
	)
}

watch(
	() => store.filters.wrafRegion,
	(newVal) => {
		if (newVal && mapRef.value) {
			multiEventsSelected()
		} else if (
			!store.drawingRegion &&
			store.selectedPointFilter === null &&
			newVal === null &&
			mapRef.value
		) {
			console.log('Resetting map bounds to last bbox', lastBbox.value)
			const map: LeafletMap = mapRef.value.leafletObject as LeafletMap
			if (lastBbox.value) {
				map.fitBounds(lastBbox.value)
			}
		}
	},
)

watch(
	() => store.wrafLevel,
	(newVal) => {
		wrafLevelChanged(store, newVal || 'none')
	},
)

const selectRegion = async (event: any) => {
	if (event.layer && event.layer.feature) {
		store.setLoading()
		await new Promise((resolve) => setTimeout(resolve, 0)) // Simulate some loading time
		const region = event.layer.feature as Feature<Polygon | MultiPolygon>
		store.selectRegion(region)
		store.setLoadingDone()
		console.log('Selected region:', region)
	} else {
		console.warn('No layer or feature found in click event:', event)
	}
}

watch(
	() => store.drawingRegion,
	(newVal) => {
		if (newVal) {
			drawRegion()
		} else {
			cancelDrawRegion()
		}
	},
)

const drawControl = computed(
	() =>
		// @ts-ignore
		new L.Draw.Polygon(map.value, {
			showArea: true,
			shapeOptions: {
				color: scssVars.c3sblue,
			},
		}),
)

const drawRegion = () => {
	// const drawnItems = new L.FeatureGroup()
	// map.value.addLayer(drawnItems)
	if (!store.drawingRegion) {
		console.warn('Already drawing a region, ignoring draw request')
		return cancelDrawRegion()
	}

	drawControl.value.enable()

	// @ts-ignore
	map.value.once(L.Draw.Event.DRAWSTOP, (event: any) => {
		// This happens whether or not a shape has been created
		// Either they finished or pressed escape
		store.drawingRegion = false
		// map.value.setView(store.mapCentre as any as LatLng, zoom.value)
	})
	// @ts-ignore
	map.value.once(L.Draw.Event.CREATED, (event: any) => {
		// This is if this shape was created
		store.setLoading()

		const layer = event.layer
		store.filters.wrafRegion = layer.toGeoJSON() as Feature<
			Polygon | MultiPolygon
		>
		store.drawingRegion = false
		store.setLoadingDone()
	})
}

const cancelDrawRegion = () => {
	drawControl.value.disable()
	// setTimeout(() => {
	// 	map.value.invalidateSize()
	// 	map.value.setView(store.mapCentre as any as LatLng, 1, {
	// 		animate: true,
	// 		duration: 0.5,
	// 		// @ts-ignore
	// 		pan: { animate: true, duration: 0.5 }, // This ensures the panning part is animated
	// 	})
	// }, 250)
}

const getEventRegion = (event: any) => {
	if (store.viewMode === 'heatmap') {
		return event.total_region || [] // We want to see the entire event footprint, because we are viewing across all times
	}
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

// TODO centralise this, so either we watch it and zoom in/out, or we do it all here and not in the store
const selectEvent = (id: string) => {
	store.selectEvent(id)
}

watch(
	() => [store.selectedTime, store.selectedEvent],
	() => {
		if (eventPixelsRef.value && eventPixelsRef.value.leafletObject) {
			eventPixelsRef.value.leafletObject.redraw()
		}
	},
)

watch(
	() => store.viewMode,
	(newVal) => {
		if (newVal === 'heatmap') {
			wmtsUrl.value = ''
		} else {
			store.regionFilteredEvents = []
			wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${store.isoDatetime}`
		}
	},
)

let pendingDone = false

function onLayerAddBatch() {
	if (!pendingDone) {
		pendingDone = true
		nextTick(() => {
			store.setLoadingDone()
			pendingDone = false
		})
	}
}

const renderTile = (props: any) =>
	drawEventTile(props, store, eventPixelsRef.value)

const pointSelectorAdded = (event: any) => {
	store.setLoadingDone()
	console.log('Marker added at', event.latlng)
	if (store.selectedPointFilter && mapRef.value) {
		// store.runFilters()
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		store.getPointFilteredEvents(lat, lng)
		store.lastPoint = [lat, lng]
	} else {
		console.warn('No point selector to add')
	}
}

const pointSelectorMoveStarted = (event: any) => {
	// console.log('Marker move started', event)
	// store.runFilters()
	store.draggingFilter = true
}

let rafId: number | null = null
const updatePointSelector = (event: LeafletMouseEvent) => {
	if (rafId) cancelAnimationFrame(rafId)
	rafId = requestAnimationFrame(() => {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		store.getPointFilteredEvents(lat, lng)
	})
}

const pointSelectorSettled = (event: any) => {
	// console.log('Marker move ended', event.latlng)
	if (store.selectedPointFilter && mapRef.value) {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		store.selectedPointFilter = [lat, lng]
		store.fixPointFilteredEvents()
		store.lastPoint = [lat, lng]
		store.draggingFilter = false
		// TODO pop up an auto-zoom button with a countdown. Two options - auto zoom in 3 seconds, or click to zoom now. Pick up the marker to cancel the zoom.
	} else {
		console.warn('No point selector to settle')
	}
}

const addEventPanes = () => {
	const map = mapRef.value?.leafletObject as LeafletMap
	if (!map) {
		console.error('Map not initialized')
		return
	}

	// create a pane just below overlayPane
	map.createPane('eventPane')
	const pane = map.getPane('eventPane')!
	// set zIndex: just under overlay (z=400)
	pane.style.zIndex = '380'

	// create a pane just below overlayPane
	map.createPane('fastEventPane')
	const fastPane = map.getPane('fastEventPane')!
	// set zIndex: just under overlay (z=400)
	fastPane.style.zIndex = '390'
}
</script>

<template>
	<div
		class="map"
		:class="{
			'have-regional': store.selectedPointFilter,
			focussed: store.isFocused,
		}"
	>
		<LMap
			ref="mapRef"
			v-model:zoom="zoom"
			:center="store.mapCentre"
			:max-zoom="12"
			:min-zoom="1"
			:options="mapOptions"
			style="z-index: 1"
			:world-copy-jump="true"
			:zoom-animation="true"
			@ready="addEventPanes"
		>
			<!-- Background layers -->
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
				v-if="store.viewMode === 'explore'"
			></LTileLayer>

			<!-- Events -->
			<!-- All of the "current" events -->
			<!-- This could just be all events if we're in heatmap mode -->
			<LPolygon
				v-for="event in currentEvents"
				:key="event.id"
				:lat-lngs="getEventRegion(event)"
				:weight="store.viewMode === 'heatmap' ? 0 : 3"
				:fill="true"
				:fill-opacity="
					store.viewMode === 'heatmap'
						? Math.min(
								0.8,
								Math.max(0.05, 1 / Math.pow(store.events.length, 0.3)),
							)
						: 0.05
				"
				:color="store.viewMode === 'heatmap' ? 'rgb(151, 24, 65)' : event.color"
				:options="{ renderer: canvasRenderer }"
				@click="selectEvent(event.id)"
			>
			</LPolygon>
			<!-- Fast filter events -->
			<LPolygon
				v-for="event in store.regionFilteredEvents"
				:key="event.id"
				:lat-lngs="event.total_region || []"
				:weight="0"
				:fill="true"
				:fill-opacity="
					Math.min(0.8, Math.max(0.05, 1 / Math.pow(store.events.length, 0.3)))
				"
				:color="scssVars.c3sred"
				:options="{ renderer: fastRenderer }"
			>
			</LPolygon>
			<!-- When an event is selected, draw a ghost trail of its regions over time -->
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
				:color="store.selectedEvent?.color || scssVars.c3sred"
				@click="selectEvent(store.selectedEvent?.id!)"
			>
			</LPolygon>
			<!-- Event pixel values -->
			<!-- Uses a custom grid layer to render event pixels otherwise it's too slow -->
			<LGridLayer
				ref="eventPixelsRef"
				:tileSize="TILE_SIZE"
				:child-render="renderTile"
				:options="{
					fadeAnimation: false,
				}"
				pane="overlayPane"
			>
			</LGridLayer>

			<!-- Selectable elements etc -->
			<!-- Possible regions to select by -->
			<LGeoJson
				v-if="store.regionsToSelectBy"
				:geojson="store.regionsToSelectBy"
				:options-style="
					() => ({
						// @ts-ignore
						className: 'region-select',
					})
				"
				class="region-select"
				@click="selectRegion"
				@add="store.setLoadingDone()"
				@layeradd="onLayerAddBatch"
			>
			</LGeoJson>
			<!-- The actual selected region -->
			<LGeoJson
				v-if="store.filters.wrafRegion"
				:geojson="store.filters.wrafRegion"
				:options-style="
					() => ({
						// @ts-ignore
						className: 'region-select',
					})
				"
				class="region-select"
				@click="store.filters.wrafRegion = null"
			>
			</LGeoJson>
			<!-- Point to select by -->
			<LMarker
				v-if="store.selectedPointFilter"
				ref="markerRef"
				:lat-lng="store.selectedPointFilter"
				:draggable="true"
				:icon="markerIcon"
				@movestart="pointSelectorMoveStarted"
				@move="updatePointSelector"
				@moveend="pointSelectorSettled"
				@add="pointSelectorAdded"
			/>

			<!-- Controls -->
			<LControl position="topright" class="the-toggle">
				<ModeToggle v-model="store.viewMode" />
			</LControl>
			<LControl position="topleft" class="region-control">
				<RegionControl v-show="store.viewMode === 'heatmap'" />
				<button
					class="filter-button"
					:class="{ heatmap: store.viewMode === 'heatmap' }"
					@click="store.filtersExpanded = !store.filtersExpanded"
				>
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
				/>
			</LControl>
			<LControlScale
				:max-width="200"
				:metric="true"
				:imperial="false"
				position="bottomright"
				class="map-scale"
			></LControlScale>
			<LControl position="bottomleft" class="panel debug"
				><div class="panel debug">{{ store.draggingFilter }}</div></LControl
			>
			<!-- <LControlZoom :class="{ shifted: store.eventSelected }"></LControlZoom> -->
		</LMap>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.map {
	width: 100%;
	height: 100%;

	.the-toggle {
		margin: $panelMargin;
	}

	:deep(.leaflet-top),
	:deep(.leaflet-bottom),
	:deep(.leaflet-left),
	:deep(.leaflet-right) {
		transition: padding $animTime ease-in-out;
	}

	&.focussed {
		:deep(.leaflet-top) {
			padding-top: calc(1 * $panelMargin);
		}
		:deep(.leaflet-left) {
			padding-left: calc(1 * $panelMargin);
		}
		:deep(.leaflet-right) {
			padding-right: calc(1 * $panelMargin);
		}
		:deep(.leaflet-bottom) {
			padding-bottom: calc(1 * $panelMargin);
		}
	}

	:deep(.leaflet-fast-event-pane) {
		opacity: 0;
	}
	:deep(.leaflet-event-pane) {
		opacity: 1;
	}
	&.have-regional {
		:deep(.leaflet-fast-event-pane) {
			opacity: 1;
		}
		:deep(.leaflet-event-pane) {
			opacity: 0;
		}
	}
	:deep(.leaflet-event-pane) {
		opacity: 1;
		transition: opacity $animTime ease-in-out;
	}

	.filter-panel {
		padding: 1rem;
		margin-top: -2.75rem;
	}

	.filter-button {
		color: white;
		background-color: $c3sblue;
		&.heatmap {
			background-color: $c3sred;
		}
	}

	:deep(.region-select) {
		stroke: rgb(0.25, 0.25, 0.25);
		stroke-width: 1px;
		fill: rgba(0, 0, 0, 0.4);
		cursor: pointer;
		&:hover {
			// cursor: pointer;
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
