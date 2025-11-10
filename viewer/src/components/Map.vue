<script setup lang="ts">
import HeatmapWorker from '@/lib/worker/heatmapRenderWorker?worker'
import {
	latLngToLayerPoint,
	renderToContext,
} from '@/lib/worker/heatmapRenderWorker'
import { debounce } from '@/lib/utils'
import { useStore } from '@/store/store'
import {
	colorForValue,
	intensityForValue,
	useStore as useEventStore,
} from '@/store/eventStore'
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
import { Map as LeafletMap, LeafletMouseEvent } from 'leaflet'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet/dist/leaflet.css'
import { computed, nextTick, ref, shallowRef, watch } from 'vue'

import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	centreMapOnDiv,
	fitBoundsToDiv,
	markerIconHot,
	markerIconCold,
	getEventRegion,
} from '@/lib/map-utils'
import { drawEventTile, TILE_SIZE } from '@/lib/renderer'
import { Feature, MultiPolygon, Polygon } from 'geojson'
import RegionControl from './util/RegionControl.vue'
import { useStore as useTimeStore } from '@/store/timeStore'
import * as d3 from 'd3'
import L from 'leaflet'
import {
	getCurrentEvents,
	setFilterToRegion,
	setFilterToPoint,
	getGlobalFilteredEvents,
	getEventCount,
	getFilteredEvents,
	onGlobalEventsReady,
	onCurrentEventsReady,
} from '@/lib/eventsDB'

const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()
const heatmapWorker = new HeatmapWorker()
const mapRef = ref<InstanceType<typeof LMap> | null>(null)
const map = computed(() => mapRef.value?.leafletObject as LeafletMap)
const eventPixelsRef = ref<InstanceType<typeof LGridLayer> | null>(null)
// create a single canvas renderer for the heatmap
const heatmapRenderer = L.canvas({ padding: 0.5, pane: 'eventPane' })
// create a single canvas renderer for the rapidly-changing filter events
const fastRenderer = L.canvas({ padding: 0.5, pane: 'fastEventPane' })

const mapOptions = {
	zoomControl: false,
	zoomSnap: 1,
	zoomDelta: 1,
	wheelPxPerZoomLevel: 240,
	fadeAnimation: false,
}

const zoom = ref(2)

const bgLayers = {
	light: {
		name: 'C3S Light',
		url: 'https://extreme-events.climate.copernicus.eu/maps/styles/light/{z}/{x}/{y}{r}.png',
		labelsUrl:
			'https://extreme-events.climate.copernicus.eu/maps/styles/light-labels/{z}/{x}/{y}{r}.png',
		attribution:
			'&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
	},
	dark: {
		name: 'C3S Dark',
		url: 'https://extreme-events.climate.copernicus.eu/maps/styles/darkish/{z}/{x}/{y}{r}.png',
		labelsUrl:
			'https://extreme-events.climate.copernicus.eu/maps/styles/dark-labels/{z}/{x}/{y}{r}.png',
		attribution:
			'&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
	},
}
const labelsOn = ref(false)

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
	console.log('Map.vue - Current events ready, updating for selected time')
	currentEvents.value = getCurrentEvents(timeStore.selectedTime)
})
const eventPointFilter = ref<[number, number] | null>(null)
const eventRegionFilter = ref<Feature<Polygon | MultiPolygon> | null>(null)
let regionFilteredEvents = [] as ExtremeEvent[]
const globalHeatmapEvents = shallowRef([] as ExtremeEvent[])
onGlobalEventsReady(() => {
	// Triggered when the global events have changed.
	// This is on first load, or when any of the high-level filters change
	// @ts-ignore
	globalHeatmapEvents.value = getGlobalFilteredEvents()
	try {
		console.log('THIS LINE HERE SHOULD BE A MANUAL BG UPDATE?')
		// @ts-ignore
		heatmapRenderer._update()
	} catch (e) {
		console.warn('Error updating heatmap renderer', e)
	}
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
		regionFilteredEvents = setFilterToRegion(eventRegionFilter.value)
		// @ts-ignore
		fastRenderer._update()
		store.regionFilterReady = true
		store.setLoadingDone()
	})
}
const cancelDrawRegion = () => {
	drawControl.value.disable()
	eventRegionFilter.value = null
}

const pointSelectorAdded = (event: any) => {
	console.log('Setting point filter', store.filteringByPoint)
	store.setLoadingDone()
	const { lat, lng } = (event.target as L.Marker).getLatLng()
	console.log('Setting point filter to', lat, lng)
	regionFilteredEvents = setFilterToPoint(lat, lng)
	try {
		// @ts-ignore
		fastRenderer._update()
	} catch (e) {
		console.warn('Error updating fast renderer', e)
	}

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
		regionFilteredEvents = getFilteredEvents()
		try {
			// @ts-ignore
			fastRenderer._update()
		} catch (e) {
			console.warn('Error updating fast renderer', e)
		}
	})
}

const pointSelectorSettled = (event: any) => {
	if (mapRef.value) {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		setFilterToPoint(lat, lng)
		regionFilteredEvents = getFilteredEvents()
		try {
			// @ts-ignore
			fastRenderer._update()
		} catch (e) {
			console.warn('Error updating fast renderer', e)
		}

		store.lastPoint = [lat, lng]
		store.draggingFilter = false
		// TODO pop up an auto-zoom button with a countdown. Two options - auto zoom in 3 seconds, or click to zoom now. Pick up the marker to cancel the zoom.
		// TODO Alternative 2 - auto-zoom, but always zoom back to the map zoom state (global by default, back to previous zoom if they had zoomed in before) when dragging the marker?
		// Both?
	} else {
		console.warn('No point selector to settle')
	}
}

const lastBbox = ref<[number, number, number, number] | null>(null)

// Watch for changes that require a redraw of the event pixels
watch(
	() => [timeStore.selectedTime, eventStore.selectedEventId, store.viewMode],
	() => {
		if (eventPixelsRef.value && eventPixelsRef.value.leafletObject) {
			eventPixelsRef.value.leafletObject.redraw()
		}
	},
)

// When the time changes, update the list of current events to draw on the map
// They will only be draw in timemachine mode, but get updated in heatmap ready for the switch back
watch(
	() => timeStore.selectedTime,
	(newVal) => {
		currentEvents.value = getCurrentEvents(newVal)
		if (wmtsUrl.value) {
			updateWmtsUrl(newVal.toISOString().split('T')[0])
		}
	},
)

// If we change what kind of events are being shown, update the heatmap and filtered events
watch(
	() => [eventStore.eventTypeMode],
	() => {
		globalHeatmapEvents.value = getGlobalFilteredEvents()
		currentEvents.value = getCurrentEvents(timeStore.selectedTime)
		if (store.viewMode === 'heatmap') {
			try {
				console.log('THIS LINE HERE SHOULD BE A MANUAL BG UPDATE?')
				// @ts-ignore
				heatmapRenderer._update()
			} catch (e) {
				console.warn('Error updating heatmap renderer', e)
			}
			if (store.filteringByPoint || store.filteringByRegion) {
				regionFilteredEvents = getFilteredEvents()
				try {
					// @ts-ignore
					fastRenderer._update()
				} catch (e) {
					console.warn('Error updating fast renderer', e)
				}
			}
		}
	},
	{ immediate: true },
)

watch(
	() => store.showMultiEventPanel,
	(newVal) => {
		if (!mapRef.value) return
		const el = document.getElementById('event-window')
		if (!el) return
		centreMapOnDiv(mapRef.value.leafletObject as L.Map, el, !newVal)
	},
	{ immediate: true },
)

// Watch for events which cause the view to change - e.g. to accomodate a panel etc.
// This is done by defining #event-window (TODO: currently in Main.vue, but could live here and teleport?)
// which changes dependent upon the rest of the screen layout. This should make adaptive views just work.
watch(
	() => [eventStore.selectedEvent, store.viewMode],
	(oldVal, newVal) => {
		// Check if the event has changed from null, in which case set lastBbox
		// TODO - is this definitely the behaviour we want?
		if (oldVal[0] === null && newVal[0] !== null) {
			lastBbox.value = (newVal[0] as ExtremeEventFull).bbox
		}

		const el = document.getElementById('event-window')
		if (!el) {
			console.warn(
				'No event window element to fit to',
				el,
				document.getElementById('event-window'),
			)
			return
		}
		// TODO this wants to be the *current* view, if we're just switching modes
		fitBoundsToDiv(
			mapRef.value!.leafletObject as L.Map,
			el,
			eventStore.selectedEvent
				? eventStore.selectedEvent.bbox
				: lastBbox.value || [-85, -180, 85, 180],
		)
	},
	{ immediate: false },
)

const cScale = computed(() => {
	const minValIntensity = intensityForValue(
		eventStore.selectedEvent?.min_value!,
		eventStore.selectedEvent?.event_type === 'hot',
	)
	const maxValIntensity = intensityForValue(
		eventStore.selectedEvent?.max_value!,
		eventStore.selectedEvent?.event_type === 'hot',
	)
	const minIntensity = Math.min(minValIntensity, maxValIntensity)
	const maxIntensity = Math.max(minValIntensity, maxValIntensity)
	return d3.scaleLinear().domain([minIntensity, maxIntensity]).range([0, 1])
})

const renderTile = (props: any) => {
	return drawEventTile(
		props,
		eventStore.selectedEvent,
		timeStore.selectedTime,
		store.viewMode,
		eventPixelsRef.value,
		(v: number) =>
			colorForValue(
				v,
				eventStore.selectedEvent?.event_type === 'hot',
				cScale.value,
			),
		(v: number) =>
			intensityForValue(v, eventStore.selectedEvent?.event_type === 'hot'),
	) as any
}

const addEventPanes = () => {
	if (!map) {
		console.error('Map not initialized')
		return
	}

	const mapPane = document.querySelector('.leaflet-map-pane')
	if (!mapPane?.querySelector('.frost-pane')) {
		const frost = document.createElement('div')
		frost.className = 'frost-pane'
		mapPane!.insertBefore(frost, mapPane!.querySelector('.leaflet-marker-pane'))
	}

	// create a pane just below overlayPane
	map.value.createPane('eventPane')
	const pane = map.value.getPane('eventPane')!
	// set zIndex: just under overlay (z=400)
	pane.style.zIndex = '380'

	heatmapRenderer.addTo(map.value)
	console.log('Added heatmap renderer at', performance.now(), heatmapRenderer)
	// When leaflet triggers an update, re-remder the heatmap on the main thread
	// Because we have already rendered this data once via the worker, GPU calculations
	// should be cached and this should be *fast*
	heatmapRenderer.on('update', () => {
		console.log('Update fired at', performance.now())
		// TODO - add pixel accurate method?
		const canvasEl = (heatmapRenderer as any)._container
		if (!canvasEl) return

		const ctxEl = canvasEl.getContext('2d')

		const events = globalHeatmapEvents.value.map((event) => ({
			total_region: [...event.total_region],
			event_type: event.event_type,
			id: event.id,
		}))
		const zoom = map.value.getZoom()
		const crs = map.value.options.crs // Usually L.CRS.EPSG3857
		// @ts-ignore
		const transformation = crs!.transformation
		const scale = crs!.scale(zoom)
		const pixelOrigin = map.value.getPixelOrigin()

		const mapState = {
			scale,
			transformation,
			pixelOrigin,
		}
		renderToContext(ctxEl, events, mapState)
	})

	// create a pane just below overlayPane
	map.value.createPane('fastEventPane')
	const fastPane = map.value.getPane('fastEventPane')!
	// set zIndex: just under overlay (z=400)
	fastPane.style.zIndex = '390'
	fastRenderer.addTo(map.value)
	fastRenderer.on('update', () => {
		const ctx = (fastRenderer as any)._ctx as CanvasRenderingContext2D
		if (!ctx) return

		ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
		ctx.globalCompositeOperation = 'multiply'

		for (const event of regionFilteredEvents) {
			ctx.beginPath()
			for (const ring of event.total_region || []) {
				// @ts-ignore
				ring.forEach(([lat, lng], i) => {
					// @ts-ignore
					const point = fastRenderer._map.latLngToLayerPoint([lat, lng])
					if (i === 0) ctx.moveTo(point.x, point.y)
					else ctx.lineTo(point.x, point.y)
				})
			}
			for (const ring of event.total_region || []) {
				// @ts-ignore
				ring.forEach(([lat, lng], i) => {
					// @ts-ignore
					const point = fastRenderer._map.latLngToLayerPoint([lat, lng + 360])
					if (i === 0) ctx.moveTo(point.x, point.y)
					else ctx.lineTo(point.x, point.y)
				})
			}
			for (const ring of event.total_region || []) {
				// @ts-ignore
				ring.forEach(([lat, lng], i) => {
					// @ts-ignore
					const point = fastRenderer._map.latLngToLayerPoint([lat, lng - 360])
					if (i === 0) ctx.moveTo(point.x, point.y)
					else ctx.lineTo(point.x, point.y)
				})
			}
			ctx.closePath()
			const alpha = Math.min(0.25, Math.max(0.1, 1000 / getEventCount()))
			ctx.fillStyle = (
				event.event_type === 'hot' ? scssVars.c3sred : scssVars.c3sblue
			)
				.replace(')', `,${alpha})`)
				.replace('rgb', 'rgba')
			ctx.fill()
		}
	})
}

// Manually trigger a heatmap update on the worker.
// When it returns, blit the bitmap to the heatmap canvas.
const manualHeatmapUpdate = () => {
	const canvasEl = (heatmapRenderer as any)._container
	if (!canvasEl) return

	const offscreen = new OffscreenCanvas(canvasEl.width, canvasEl.height)
	const events = globalHeatmapEvents.value.map((event) => ({
		total_region: [...event.total_region],
		event_type: event.event_type,
		id: event.id,
	}))
	const zoom = map.value.getZoom()
	const crs = map.value.options.crs // Usually L.CRS.EPSG3857
	// @ts-ignore
	const transformation = crs!.transformation
	const scale = crs!.scale(zoom)
	const pixelOrigin = map.value.getPixelOrigin()

	heatmapWorker.postMessage(
		{
			canvas: offscreen,
			events,
			mapState: {
				scale,
				transformation,
				pixelOrigin,
			},
		},
		[offscreen],
	)
}
// Takes care of the blitting on the worker's return
heatmapWorker.onmessage = (e) => {
	if (e.data.bitmap) {
		const canvasEl = (heatmapRenderer as any)._container
		const ctxEl = canvasEl.getContext('2d')
		if (ctxEl) {
			ctxEl.clearRect(0, 0, canvasEl.width, canvasEl.height)
			ctxEl.drawImage(e.data.bitmap, 0, 0)
		}
	}
}

const showMarker = computed(
	() => store.filteringByPoint && store.viewMode === 'heatmap',
)
// const showMarkerTrigger = computed(
// 	() => store.filteringByPoint && store.viewMode === 'heatmap',
// )
// const showMarker = ref(showMarkerTrigger.value)
// watch(
// 	showMarkerTrigger,
// 	(newVal) => {
// 		nextTick(() => {
// 			showMarker.value = newVal
// 		})
// 	},
// 	{ immediate: true },
// )
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
			heatmap: store.viewMode === 'heatmap',
			timemachine: store.viewMode === 'timemachine',
		}"
	>
		<LMap
			ref="mapRef"
			v-model:zoom="zoom"
			:center="store.mapCentre"
			:max-zoom="12"
			:min-zoom="2"
			:options="mapOptions"
			style="z-index: 1"
			:world-copy-jump="true"
			:zoom-animation="true"
			@ready="addEventPanes"
		>
			<!-- Background layers -->
			<LTileLayer
				:url="bgLayers.light.url"
				:attribution="bgLayers.light.attribution"
				layer-type="base"
				:opacity="store.viewMode === 'heatmap' ? 1 : 0"
				:zIndex="1"
			></LTileLayer>
			<LTileLayer
				:url="bgLayers.dark.url"
				:attribution="bgLayers.dark.attribution"
				layer-type="base"
				:opacity="store.viewMode === 'timemachine' ? 1 : 0"
				:zIndex="2"
			></LTileLayer>
			<!-- <LTileLayer
				class="bg-map"
				:url="wmtsUrl"
				:zIndex="5"
				:opacity="0.75"
				v-if="store.viewMode === 'timemachine'"
			></LTileLayer> -->

			<!-- Events -->
			<!-- Current events as polygons -->
			<LPolygon
				v-if="store.viewMode === 'timemachine'"
				v-for="event in currentEvents"
				:key="`ev-${event.id}-${timeStore.selectedTime.toISOString()}`"
				:lat-lngs="getEventRegion(event, timeStore.selectedTime)"
				:weight="event.id === eventStore.selectedEventId ? 4 : 2"
				:fill="true"
				:fill-opacity="event.id === eventStore.selectedEventId ? 0.0 : 0.5"
				:color="
					event.id === eventStore.selectedEventId
						? scssVars.lightbulb
						: eventStore.colorForEvent(event)
				"
				:fill-color="eventStore.colorForEvent(event)"
				@click="eventStore.selectEvent(event.id)"
			>
			</LPolygon>
			<!-- Heatmap and fast filter events have now moved to their own renderers. They are blisteringly fast -->
			<!-- They were previously loops of LPolygon components, like this, but it proved too slo -->

			<!-- Event pixel values -->
			<!-- Uses a custom grid layer to render event pixels otherwise it's too slow -->
			<LGridLayer
				v-if="eventStore.selectedEvent"
				ref="eventPixelsRef"
				:tileSize="TILE_SIZE"
				:child-render="renderTile"
				:options="{
					fadeAnimation: false,
				}"
				pane="markerPane"
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
			<div v-if="store.filteringByPoint && store.viewMode === 'heatmap'">
				<LMarker
					ref="markerRef"
					:lat-lng="eventPointFilter || store.lastPoint || [50.70636, 7.138647]"
					:draggable="true"
					:icon="
						(eventStore.eventTypeMode === 'cold'
							? markerIconCold
							: markerIconHot) as any
					"
					@movestart="pointSelectorMoveStarted"
					@move="updatePointSelector"
					@moveend="pointSelectorSettled"
					@add="pointSelectorAdded"
				/>
			</div>

			<!-- Controls -->
			<LControl position="topleft" class="region-control">
				<RegionControl
					:class="{
						hidden:
							store.viewMode !== 'heatmap' || eventStore.selectedEvent !== null,
					}"
				/>
			</LControl>
			<LControlScale
				:max-width="200"
				:metric="true"
				:imperial="false"
				position="bottomright"
				class="map-scale"
			></LControlScale>
		</LMap>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.map {
	width: 100%;
	height: 100%;

	// This matches the default map theme, so that it's white at the bottom
	// to jut up against antarctica, grey at the top for arctic ocean
	.leaflet-container {
		background: linear-gradient(
			to top,
			rgb(249, 249, 249),
			rgb(249, 249, 249) 49%,
			rgb(195, 200, 202) 51%,
			rgb(195, 200, 202)
		);
	}

	.the-toggle {
		margin: $panelMargin;
	}

	.event-type-toggle {
		top: 0;
		left: 50%;
		transform: translateX(-50%);
		position: absolute;
		z-index: 1000;
	}

	.region-control {
		&.hidden {
			transform: translateY(-250%);
		}
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

	:deep(.leaflet-fastEvent-pane) {
		opacity: 0;
	}
	:deep(.leaflet-event-pane) {
		opacity: 0;
		transition: opacity $animTime ease-in-out;
	}

	&.heatmap {
		:deep(.leaflet-event-pane) {
			opacity: 1;
		}
	}
	&.have-regional {
		:deep(.leaflet-fastEvent-pane) {
			opacity: 1;
		}
		:deep(.leaflet-event-pane) {
			opacity: 0;
		}
	}
	&.dragging {
		:deep(.leaflet-fastEvent-pane) {
			opacity: 1;
		}
		:deep(.leaflet-event-pane) {
			opacity: 0.1;
		}
	}
	&.timemachine {
		:deep(.leaflet-event-pane) {
			opacity: 0;
		}
		:deep(.leaflet-fastEvent-pane) {
			opacity: 0;
		}
	}

	.filter-panel {
		padding: 1rem;
		margin-top: -2.75rem;
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

	:deep(.leaflet-tile) {
		image-rendering: pixelated; /* or auto/smooth depending on your preference */
		transform-origin: center center;
	}

	:deep(.leaflet-tile-pane) {
		.leaflet-layer {
			transition: opacity $transition;
		}
	}

	&.focussed {
		:deep(.frost-pane) {
			background-color: rgba(200, 200, 200, 0.5);
			backdrop-filter: blur(4px);

			pointer-events: none;
			position: fixed;
			top: -500vh;
			left: -500vh;
			width: 1100vw;
			height: 1100vh;
			z-index: 450;
		}

		&.heatmap {
			:deep(.frost-pane) {
				background-color: rgba(0, 0, 0, 0.5);
			}
		}
	}
}
</style>
