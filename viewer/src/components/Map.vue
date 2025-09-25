<script setup lang="ts">
import { debounce } from '@/lib/utils'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
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
import { LatLngBounds, Map as LeafletMap, LeafletMouseEvent } from 'leaflet'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet/dist/leaflet.css'
import { computed, nextTick, ref, watch } from 'vue'

import scssVars from '@/assets/styles/scssVars.module.scss'
import { markerIcon } from '@/lib/map-utils'
import { drawEventTile, TILE_SIZE } from '@/lib/renderer'
import { faClose, faFilter } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { Feature, MultiPolygon, Polygon } from 'geojson'
import FilterPanel from './FilterPanel.vue'
import RegionControl from './util/RegionControl.vue'
import { useStore as useTimeStore } from '@/store/timeStore'

const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const map = computed(() => mapRef.value?.leafletObject as LeafletMap)
const eventPixelsRef = ref<InstanceType<typeof LGridLayer> | null>(null)

import L from 'leaflet'
import ModeToggle from './util/ModeToggle.vue'
import {
	getCurrentEvents,
	setFilterToRegion,
	setFilterToPoint,
	clearFilter,
	getGlobalFilteredEvents,
	getEventCount,
	getFilteredEvents,
	onGlobalEventsReady,
	onRegionEventsReady,
	onCurrentEventsReady,
} from '@/lib/eventFiltering'
// create a single canvas renderer for all polygons
const canvasRenderer = L.canvas({ padding: 0.5, pane: 'eventPane' })
canvasRenderer.on('update', () => {
	const ctx = (canvasRenderer as any)._ctx as CanvasRenderingContext2D
	if (ctx) ctx.globalCompositeOperation = 'multiply'
})
const fastRenderer = L.canvas({ padding: 0.5, pane: 'fastEventPane' })
fastRenderer.on('update', () => {
	const ctx = (fastRenderer as any)._ctx as CanvasRenderingContext2D
	if (ctx) ctx.globalCompositeOperation = 'multiply'
})

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
	`https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${timeStore.isoDatetime}`,
)
const updateWmtsUrl = debounce((newVal: string) => {
	console.log(
		'Updating WMTS URL to:',
		newVal,
		' (nah, not really. You should probably uncomment the next line at some point)',
	)
	// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
}, 500)
watch(() => timeStore.isoDatetime, updateWmtsUrl)

watch(
	() => store.filteringByRegion,
	(newVal) => {
		// This turns the region drawing control on or off
		// No such thing is needed for the point selector, which is a marker defined in the templates
		if (newVal) {
			drawRegion()
		} else {
			cancelDrawRegion()
		}
	},
)

// The draw control for defining regions
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

const currentEvents = ref<ExtremeEvent[]>([])
onCurrentEventsReady(() => {
	// This gets called when the time index is ready
	currentEvents.value = getCurrentEvents(timeStore.selectedTime)
})
const eventPointFilter = ref<[number, number] | null>(null)
const eventRegionFilter = ref<Feature<Polygon | MultiPolygon> | null>(null)
const regionFilteredEvents = ref([] as ExtremeEvent[])
const globalHeatmapEvents = ref([] as ExtremeEvent[])
onGlobalEventsReady(() => {
	// Triggered when the global events have changed.
	// This is on first load, or when any of the high-level filters change
	// @ts-ignore
	globalHeatmapEvents.value = getGlobalFilteredEvents()
})

const drawRegion = () => {
	drawControl.value.enable()

	// @ts-ignore
	map.value.once(L.Draw.Event.DRAWSTOP, (event: any) => {
		// This happens whether or not a shape has been created
		// Either they finished or pressed escape
		// map.value.setView(store.mapCentre as any as LatLng, zoom.value)
	})
	// @ts-ignore
	map.value.once(L.Draw.Event.CREATED, (event: any) => {
		// This is if this shape was created
		store.setLoading()
		const layer = event.layer
		eventRegionFilter.value = layer.toGeoJSON() as Feature<
			Polygon | MultiPolygon
		>
		regionFilteredEvents.value = setFilterToRegion(eventRegionFilter.value)
		store.regionFilterReady = true
		store.setLoadingDone()
	})
}
const cancelDrawRegion = () => {
	drawControl.value.disable()
	eventRegionFilter.value = null
	clearFilter()
}

const pointSelectorAdded = (event: any) => {
	console.log('Setting point filter', store.filteringByPoint)
	store.setLoadingDone()
	const { lat, lng } = (event.target as L.Marker).getLatLng()
	console.log('Setting point filter to', lat, lng)
	regionFilteredEvents.value = setFilterToPoint(lat, lng)
	store.lastPoint = [lat, lng]
	console.log('Set point filter to', lat, lng)
}
const pointSelectorMoveStarted = (event: any) => {
	store.draggingFilter = true
}

let rafId: number | null = null
const updatePointSelector = (event: LeafletMouseEvent) => {
	if (rafId) cancelAnimationFrame(rafId)
	rafId = requestAnimationFrame(() => {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		setFilterToPoint(lat, lng)
		regionFilteredEvents.value = getFilteredEvents()
	})
}

const pointSelectorSettled = (event: any) => {
	if (mapRef.value) {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		setFilterToPoint(lat, lng)
		regionFilteredEvents.value = getFilteredEvents()
		store.lastPoint = [lat, lng]
		store.draggingFilter = false
		// TODO pop up an auto-zoom button with a countdown. Two options - auto zoom in 3 seconds, or click to zoom now. Pick up the marker to cancel the zoom.
		// TODO Alternative 2 - auto-zoom, but always zoom back to the map zoom state (global by default, back to previous zoom if they had zoomed in before) when dragging the marker?
		// Both?
	} else {
		console.warn('No point selector to settle')
	}
}

// Extract the region for a given event at the currently selected time
// This is for the timemachine mode, updates the "current" events as we drag/animate the time slider
const getEventRegion = (event: ExtremeEvent) => {
	const selected = timeStore.selectedTime.getTime()
	const idx = event.times
		.map((t: Date) => t.getTime())
		.findIndex((t) => t === selected)

	if (idx < 0) {
		console.warn(
			`No region found for event ${event.id} at time ${timeStore.selectedTime.toISOString()}`,
		)
		return event.regions[0] || [] // Fallback to first region if no matching time found
	}
	return event.regions[idx] || [] // Fallback to empty array if no region found
}

const lastBbox = ref<LatLngBounds | null>(null)

watch(
	() => [timeStore.selectedTime, eventStore.selectedEventId],
	() => {
		if (eventPixelsRef.value && eventPixelsRef.value.leafletObject) {
			eventPixelsRef.value.leafletObject.redraw()
		}
	},
)

watch(
	() => timeStore.selectedTime,
	(newVal) => {
		currentEvents.value = getCurrentEvents(newVal)
		if (store.viewMode === 'heatmap') {
			globalHeatmapEvents.value = getGlobalFilteredEvents()
		}
		if (wmtsUrl.value) {
			updateWmtsUrl(newVal.toISOString().split('T')[0])
		}
	},
)

watch(
	() => eventStore.selectedEvent,
	(event) => {
		if (!event || !map.value) return
		map.value.fitBounds(
			[
				[event.bbox[0], event.bbox[1]],
				[event.bbox[2], event.bbox[3]],
			],
			{
				paddingTopLeft: [64, 64],
				paddingBottomRight: [32, map.value.getSize().y * 0.5 + 32],
				maxZoom: 12,
				// @ts-ignore
				duration: scssVars.animTime,
			},
		)
	},
	{ immediate: true },
)

watch(
	() => store.viewMode,
	(newVal) => {
		if (newVal === 'heatmap') {
			wmtsUrl.value = ''
		} else {
			wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${timeStore.isoDatetime}`
		}
	},
)

const renderTile = (props: any) =>
	drawEventTile(
		props,
		eventStore.selectedEvent,
		timeStore.selectedTime,
		store.viewMode,
		eventStore.intensityRange,
		eventPixelsRef.value,
	)

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
			'have-regional':
				store.viewMode === 'heatmap' &&
				(store.filteringByPoint ||
					(store.regionFilterReady && store.filteringByRegion)),
			dragging: store.draggingFilter,
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
				v-if="store.viewMode === 'timemachine'"
			></LTileLayer>

			<!-- Events -->
			<!-- All of the "current" events -->
			<!-- This could just be all events if we're in heatmap mode -->
			<LPolygon
				v-if="store.viewMode === 'heatmap'"
				v-for="event of globalHeatmapEvents"
				:key="`hm-${event.id}`"
				:lat-lngs="event.total_region || []"
				:weight="0"
				:fill="true"
				:fill-opacity="0.1"
				:color="'rgb(151, 24, 65)'"
				:options="{ renderer: canvasRenderer }"
				@click="eventStore.selectEvent(event.id)"
			>
			</LPolygon>
			<LPolygon
				v-else
				v-for="event in currentEvents"
				:key="`ev-${event.id}-${timeStore.selectedTime.toISOString()}`"
				:lat-lngs="getEventRegion(event)"
				:weight="2"
				:fill="true"
				:fill-opacity="0.1"
				:color="scssVars.c3sblue"
				:fill-color="eventStore.colorForEvent(event)"
				@click="eventStore.selectEvent(event.id)"
			>
			</LPolygon>
			<!-- Fast filter events. We want to update these while dragging, so they need to be fast -->
			<LPolygon
				v-if="store.viewMode === 'heatmap'"
				v-for="event in regionFilteredEvents"
				:key="event.id"
				:lat-lngs="event.total_region || []"
				:weight="0"
				:fill="true"
				:fill-opacity="Math.min(0.8, Math.max(0.05, 1 / getEventCount()))"
				:color="scssVars.c3sred"
				:options="{ renderer: fastRenderer }"
			>
			</LPolygon>
			<!-- When an event is selected, draw a ghost trail of its regions over time -->
			<!-- <LPolygon
				v-if="store.viewMode !== 'heatmap' && eventStore.eventSelected"
				v-for="(region, idx) in eventStore.selectedEvent!.regions"
				:key="idx"
				:lat-lngs="region"
				:weight="1"
				:fill="false"
				:opacity="
					eventStore.selectedEvent
						? getZeitgeistOpacity(
								Math.abs(
									differenceInDays(
										timeStore.selectedTime,
										eventStore.selectedEvent.times[idx],
									),
								),
							)
						: 0
				"
				:color="eventStore.selectedEvent?.color || scssVars.c3sred"
				@click="selectEvent(eventStore.selectedEvent?.id!)"
			>
			</LPolygon> -->
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
			<!-- The actual selected region -->
			<LGeoJson
				v-if="eventRegionFilter && store.viewMode === 'heatmap'"
				:key="`region-draw`"
				:geojson="eventRegionFilter"
				:options-style="
					() => ({
						// @ts-ignore
						className: 'region-select',
					})
				"
				class="region-select"
				@click="console.log('Clicked region')"
			></LGeoJson>

			<!-- Point to select by -->
			<LMarker
				v-if="store.filteringByPoint && store.viewMode === 'heatmap'"
				ref="markerRef"
				:lat-lng="eventPointFilter || store.lastPoint || [20, 0]"
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
							max: eventStore.durationRange
								? Math.min(14, eventStore.durationRange[1])
								: 7,
						},
						{
							key: 'intensity',
							label: 'Intensity',
							type: 'range',
							pass: 'high-pass',
							min: eventStore.intensityRange
								? eventStore.intensityRange[0]
								: 300,
							max: eventStore.intensityRange
								? eventStore.intensityRange[1]
								: 350,
						},
						{
							key: 'size',
							label: 'Size',
							type: 'range',
							pass: 'high-pass',
							min: eventStore.sizeRange ? eventStore.sizeRange[0] : 1000,
							max: eventStore.sizeRange ? eventStore.sizeRange[1] : 10000,
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
				><div class="panel debug">
					{{ regionFilteredEvents.length }}
				</div></LControl
			>
			<!-- <LControlZoom :class="{ shifted: eventStore.eventSelected }"></LControlZoom> -->
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
	&.dragging {
		:deep(.leaflet-fast-event-pane) {
			opacity: 0.67;
		}
		:deep(.leaflet-event-pane) {
			opacity: 0.33;
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
