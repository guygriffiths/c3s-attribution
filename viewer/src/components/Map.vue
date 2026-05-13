<script setup lang="ts">
import HeatmapWorker from '@/lib/worker/heatmapRenderWorker?worker'
import { renderToContext } from '@/lib/worker/heatmapRenderWorker'
import { ECMWF_BONN } from '@/lib/utils'
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
import HelpButton from './util/HelpButton.vue'
import { useStore as useTimeStore } from '@/store/timeStore'
import * as d3 from 'd3'
import L from 'leaflet'
import {
	getCurrentEvents,
	setFilterToRegion,
	setFilterToPoint,
	clearSpatialFilter,
	onParameterFilterChanged,
	onSpatialFilterChanged,
	getParameterFilteredEvents,
	getSpatiallyFilteredEvents,
	getSpaceTimeFilteredEvents,
	onTimeFilterChanged,
	onSpaceTimeFilterChanged,
	getTimeFilteredEvents,
} from '@/lib/eventsDB'
import { IconZoomIn, IconZoomOut, IconZoomReset } from '@tabler/icons-vue'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
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
		url: 'https://extreme-events.climate.copernicus.eu/maps/styles/c3s-light/{z}/{x}/{y}{r}.png',
		labelsUrl:
			'https://extreme-events.climate.copernicus.eu/maps/styles/light-labels/{z}/{x}/{y}{r}.png',
		attribution:
			'&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
	},
	dark: {
		name: 'C3S Dark',
		url: 'https://extreme-events.climate.copernicus.eu/maps/styles/c3s-time-machine/{z}/{x}/{y}{r}.png',
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
// const updateWmtsUrl = debounce((newVal: string) => {
// console.log(
// 	'Updating WMTS URL to:',
// 	newVal,
// 	' (nah, not really. You should probably uncomment the next line at some point)',
// )
// wmtsUrl.value = `https://cadl2-wmts.lobelia.earth/teroWmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&FORMAT=image/png&LAYER=reanalysis_era5_single_levels/sfc/t2m&STYLE=cmap:magma&TILEMATRIXSET=EPSG:3857@2x&TILEMATRIX={z}&TILECOL={x}&TILEROW={y}&TIME=${newVal}`
// }, 500)

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

watch(
	() => store.filteringByPoint,
	(newVal) => {
		if (!newVal) {
			clearSpatialFilter()
			currentEvents.value = getCurrentEvents(timeStore.selectedTime, true)
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
				color:
					eventStore.eventTypeMode === 'hot'
						? scssVars.c3sblue
						: eventStore.eventTypeMode === 'cold'
							? scssVars.c3sred
							: scssVars.c3sgreen,
			},
		}),
)

const currentEvents = ref<ExtremeEvent[]>([])
onParameterFilterChanged(() => {
	// globalHeatmapEvents and manualHeatmapUpdate are handled by onTimeFilterChanged,
	// which always fires downstream after buildParameterFilterResults rebuilds the chain.
	currentEvents.value = getCurrentEvents(timeStore.selectedTime, true)
	if (store.viewMode === 'heatmap') {
		try {
			manualHeatmapUpdate()
		} catch (e) {
			console.warn('Error updating heatmap renderer', e)
		}
	}
})
onSpatialFilterChanged(() => {
	// _spatiallyFilteredEventIds is now up to date — safe to refresh currentEvents
	regionFilteredEvents = getSpatiallyFilteredEvents()
	currentEvents.value = getCurrentEvents(timeStore.selectedTime, true)
	try {
		// @ts-ignore
		fastRenderer._update()
	} catch (e) {
		console.warn('Error updating fast renderer', e)
	}
})
onTimeFilterChanged(() => {
	// This will only happen in heatmap mode
	// console.log('Time filter changed, updating heatmap events')

	// When the time filter changes, we need to update the current events
	globalHeatmapEvents.value = getTimeFilteredEvents()
	try {
		manualHeatmapUpdate()
		// @ts-ignore
		fastRenderer._update()
	} catch (e) {
		console.warn('Error updating heatmap renderer', e)
	}
})
onSpaceTimeFilterChanged(() => {
	// This will only happen in heatmap mode
	// console.log('spacetime filter changed, updating heatmap events')

	// When the time filter changes, we need to update the current events
	regionFilteredEvents = getSpaceTimeFilteredEvents()
	try {
		// @ts-ignore
		fastRenderer._update()
	} catch (e) {
		console.warn('Error updating heatmap renderer', e)
	}
})

const eventPointFilter = ref<[number, number] | null>(null)
const eventRegionFilter = ref<Feature<Polygon | MultiPolygon> | null>(null)
const regionKey = ref(0)
let regionFilteredEvents = [] as ExtremeEvent[]
const globalHeatmapEvents = shallowRef([] as ExtremeEvent[])

const regionHovered = ref(false)
let regionHoverOutTimer: ReturnType<typeof setTimeout> | null = null

const keepRegionHovered = () => {
	if (regionHoverOutTimer) {
		clearTimeout(regionHoverOutTimer)
		regionHoverOutTimer = null
	}
	regionHovered.value = true
}
const scheduleRegionUnhover = () => {
	regionHoverOutTimer = setTimeout(() => {
		regionHovered.value = false
	}, 2000)
}

const closeBoxPosition = computed<[number, number] | null>(() => {
	if (!eventRegionFilter.value) return null
	const geom = eventRegionFilter.value.geometry
	const ring: number[][] =
		geom.type === 'Polygon' ? geom.coordinates[0] : geom.coordinates[0][0]
	const maxLat = ring.reduce((m, c) => Math.max(m, c[1]), -Infinity)
	const maxLng = ring.reduce((m, c) => Math.max(m, c[0]), -Infinity)
	const closest = ring.reduce((best, c) => {
		const d = (c[1] - maxLat) ** 2 + (c[0] - maxLng) ** 2
		const bd = (best[1] - maxLat) ** 2 + (best[0] - maxLng) ** 2
		return d < bd ? c : best
	})
	return [closest[1], closest[0]]
})

const closeRegionIcon = L.divIcon({
	className: 'close-region-marker',
	html: `<button class="button glassy color"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" size="24" aria-hidden="true" class="tabler-icon tabler-icon-x"><path d="M18 6l-12 12"></path><path d="M6 6l12 12"></path></svg></button>`,
	iconSize: [32, 32],
	iconAnchor: [0, 32],
})

const clearRegionFilter = () => {
	store.filteringByRegion = false
	store.regionFilterReady = false
}

const drawRegion = () => {
	drawControl.value.enable()

	// @ts-ignore
	map.value.once(L.Draw.Event.DRAWSTOP, (event: any) => {
		// This happens whether or not a shape has been created
		// Either they finished or pressed escape
		// map.value.setView(store.mapCentre as any as LatLng, zoom.value)
	})
	// @ts-ignore
	map.value.once(L.Draw.Event.CREATED, async (event: any) => {
		// This is if this shape was created
		await store.setLoading('Applying region filter...')
		const layer = event.layer
		eventRegionFilter.value = layer.toGeoJSON() as Feature<
			Polygon | MultiPolygon
		>
		regionKey.value++
		await nextTick()
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
	clearSpatialFilter()
	currentEvents.value = getCurrentEvents(timeStore.selectedTime, true)
}

const pointSelectorAdded = (event: any) => {
	// console.log('Setting point filter', store.filteringByPoint)
	const { lat, lng } = (event.target as L.Marker).getLatLng()
	// console.log('Setting point filter to', lat, lng)
	regionFilteredEvents = setFilterToPoint(lat, lng)
	try {
		// @ts-ignore
		fastRenderer._update()
	} catch (e) {
		console.warn('Error updating fast renderer', e)
	}

	store.lastPoint = [lat, lng]
	// console.log('Set point filter to', lat, lng)
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
	})
}

const pointSelectorSettled = (event: any) => {
	if (mapRef.value) {
		const { lat, lng } = (event.target as L.Marker).getLatLng()
		setFilterToPoint(lat, lng)

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
	() => [timeStore.selectedTime, eventStore.selectedEvent, store.viewMode],
	() => {
		if (eventPixelsRef.value && eventPixelsRef.value.leafletObject) {
			eventPixelsRef.value.leafletObject.redraw()
		}
	},
)

// When the time or spatial filter changes, update the list of current events to draw on the map
// They will only be drawn in timemachine mode, but get updated in heatmap ready for the switch back
watch(
	() => [
		timeStore.selectedTime,
		store.regionFilterReady,
	],
	([time]) => {
		currentEvents.value = getCurrentEvents(time as Date, true)
		// if (wmtsUrl.value) {
		// 	updateWmtsUrl((time as Date).toISOString().split('T')[0])
		// }
	},
)

// Watch for events which cause the view to change - e.g. to accomodate a panel etc.
// This is done by defining #event-window (TODO: currently in Main.vue, but could live here and teleport?)
// which changes dependent upon the rest of the screen layout. This should make adaptive views just work.
watch(
	() => [eventStore.selectedEvent, store.viewMode],
	(oldVal, newVal) => {
		// Check if the event has changed from null, in which case set lastBbox
		// TODO - is this definitely the behaviour we want?
		// if (oldVal[0] === null && newVal[0] !== null) {
		// 	lastBbox.value = (newVal[0] as ExtremeEventFull).bbox
		// }

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
		eventStore.selectedEvent?.event_type === 'hot' || eventStore.selectedEvent?.event_type === 'cold',
	)
	const maxValIntensity = intensityForValue(
		eventStore.selectedEvent?.max_value!,
		eventStore.selectedEvent?.event_type === 'hot' || eventStore.selectedEvent?.event_type === 'cold',
	)
	const minIntensity = Math.min(minValIntensity, maxValIntensity)
	const maxIntensity = Math.max(minValIntensity, maxValIntensity)
	return eventStore.selectedEvent?.event_type === 'hot'
		? d3.scaleLinear().domain([minIntensity, maxIntensity]).range([0, 1])
		: d3.scaleLinear().domain([minIntensity, maxIntensity]).range([1, 0])
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
				eventStore.selectedEvent?.event_type ?? 'hot',
				cScale.value,
			),
		(v: number) =>
			intensityForValue(v, eventStore.selectedEvent?.event_type !== 'wet'),
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
	// When leaflet triggers an update, re-remder the heatmap on the main thread
	// Because we have already rendered this data once via the worker, GPU calculations
	// should be cached and this should be *fast*
	//
	// TODO - NOt technically true. I have sent it empty data to prime the cache, which works.
	// But I don;'t know why.
	heatmapRenderer.on('update', () => {
		// TODO - add pixel accurate method?
		const canvasEl = (heatmapRenderer as any)._container
		if (!canvasEl) return

		const ctxEl = canvasEl.getContext('2d')

		const events = globalHeatmapEvents.value?.map((event) => ({
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

	// create a pane for the hover total_region polygon — below overlayPane (400) so daily regions render on top
	map.value.createPane('hoverPane')
	map.value.getPane('hoverPane')!.style.zIndex = '395'

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
			const alpha = 0.1
			// Math.min(
			// 	0.25,
			// 	Math.max(0.0, 250 / globalHeatmapEvents.value.length),
			// )
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
	if (!canvasEl) {
		console.warn('No canvas element for heatmap renderer')
		return
	}

	// Apparently this is enough to precache whatever was slowing it down.
	const offscreen = new OffscreenCanvas(canvasEl.width, canvasEl.height)
	heatmapWorker.postMessage(
		{
			canvas: offscreen,
			events: [],
			mapState: {},
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
		} else {
			console.warn('No canvas element for heatmap renderer')
		}
		// @ts-ignore
		heatmapRenderer._update()
	}
}

const zoomIn = () => {
	if (map.value) {
		map.value.zoomIn()
	}
}
const zoomOut = () => {
	if (map.value) {
		map.value.zoomOut()
	}
}
const resetZoom = () => {
	fitBoundsToDiv(
		mapRef.value!.leafletObject as L.Map,
		document.getElementById('event-window')!,
		[-70, -180, 85, 180],
	)
}
const mapClicked = (event: LeafletMouseEvent) => {
	if (store.filteringByPoint) {
		// Move the point selector to the clicked location
		store.lastPoint = [event.latlng.lat, event.latlng.lng]
	}
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
			@click="mapClicked"
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
			<!-- Hovered event: full total_region in hoverPane (z=395), always behind overlayPane daily regions (z=400) -->
			<LPolygon
				v-if="eventStore.hoveringEvent"
				:key="`ev-${eventStore.hoveringEvent.id}-hover`"
				:lat-lngs="eventStore.hoveringEvent.total_region"
				:weight="0"
				:fill="true"
				:fill-opacity="0.8"
				:color="scssVars.lightbulb"
				:fill-color="scssVars.lightbulb"
				:options="{ interactive: false, pane: 'hoverPane' }"
			>
			</LPolygon>
			<!-- Current events as daily-region polygons (timemachine only) -->
			<!-- Hovered event has a thicker stroke and no fill so it stands out against the total_region overlay -->
			<LPolygon
				v-if="store.viewMode === 'timemachine'"
				v-for="event in [eventStore.hoveringEvent, ...currentEvents]
					.filter((e) => e !== null)
					.filter((e, i, arr) => arr.findIndex((x) => x.id === e.id) === i)"
				:key="`ev-${event.id}-${timeStore.selectedTime.toISOString()}`"
				:lat-lngs="getEventRegion(event, timeStore.selectedTime)"
				:weight="
					event.id === eventStore.selectedEventId
						? 2
						: event.id === eventStore.hoveringEvent?.id
							? 1.5
							: 0.5
				"
				:fill="true"
				:fill-opacity="
					event.id === eventStore.selectedEventId ||
					event.id === eventStore.hoveringEvent?.id
						? 1
						: 0.5
				"
				:color="
					event.event_type === 'hot'
						? scssVars.c3sred
						: event.event_type === 'cold'
							? scssVars.c3sblue
							: scssVars.c3sgreen
				"
				:fill-color="eventStore.colorForEvent(event)"
				@click="eventStore.selectEvent(event)"
				@mouseover="eventStore.setHoveringEvent(event)"
				@mouseout="eventStore.setHoveringEvent(null)"
			>
			</LPolygon>

			<!-- Heatmap and fast filter events have now moved to their own renderers. They are blisteringly fast -->
			<!-- They were previously loops of LPolygon components, like this, but it proved too slow for interactive use -->

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
				v-if="eventRegionFilter"
				:key="`region-draw-${regionKey}`"
				:geojson="eventRegionFilter"
				:options-style="
					() => ({
						// @ts-ignore
						className: 'region-select',
					})
				"
				@mouseover="keepRegionHovered"
				@mouseout="scheduleRegionUnhover"
			></LGeoJson>
			<LMarker
				v-if="regionHovered && closeBoxPosition"
				:lat-lng="closeBoxPosition"
				:icon="closeRegionIcon as any"
				@click="clearRegionFilter"
				@mouseover="keepRegionHovered"
				@mouseout="scheduleRegionUnhover"
			/>

			<!-- Point to select by -->
			<div v-if="store.filteringByPoint">
				<LMarker
					ref="markerRef"
					:lat-lng="eventPointFilter || store.lastPoint || ECMWF_BONN"
					:draggable="true"
					:icon="
						(eventStore.eventTypeMode === 'cold'
							? markerIconCold
							: markerIconHot) as any
					"
					:options-style="
						() => ({
							className: store.viewMode === 'heatmap' ? 'active' : 'inactive',
						})
					"
					@movestart="pointSelectorMoveStarted"
					@move="updatePointSelector"
					@moveend="pointSelectorSettled"
					@add="pointSelectorAdded"
				/>
			</div>

			<!-- Controls -->
			<LControl
				position="topright"
				class="zoom-control"
				:class="{ hidden: eventStore.selectedEvent !== null }"
				:inert="eventStore.selectedEvent !== null ? 'true' : undefined"
			>
				<div class="zoom-buttons">
					<button
						class="zoom-button glassy"
						@click="zoomOut()"
						:disabled="zoom <= 2"
						v-tooltip="$l.zoomOut"
					>
						<IconZoomOut aria-hidden="true" />
					</button>
					<button
						class="zoom-button glassy"
						@click="resetZoom()"
						v-tooltip="$l.resetZoom"
					>
						<IconZoomReset aria-hidden="true" />
					</button>

					<button
						class="zoom-button glassy"
						@click="zoomIn()"
						:disabled="zoom >= 12"
						v-tooltip="$l.zoomIn"
					>
						<IconZoomIn aria-hidden="true" />
					</button>
				</div>
			</LControl>
			<LControl position="topleft" class="region-control">
				<RegionControl
					:class="{
						hidden:
							eventStore.selectedEvent !== null || store.maximizeMultiPanel,
					}"
					:inert="
						eventStore.selectedEvent !== null || store.maximizeMultiPanel
							? 'true'
							: undefined
					"
				>
					<HelpButton help="regionControl" />
				</RegionControl>
			</LControl>
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
		background: rgb(95, 102, 110);
	}

	&.heatmap {
		.leaflet-container {
			background: linear-gradient(
				to top,
				rgb(249, 249, 249),
				rgb(249, 249, 249) 49%,
				rgb(195, 200, 202) 51%,
				rgb(195, 200, 202)
			);
		}
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
		pointer-events: all;
		transform: translate(0.5rem, 1.75rem);
		&.hidden {
			transform: translate(-150%, 2rem);
		}
		transition: transform $transition;

		button {
			transform: translate(-50%, -50%);
			width: 1.75rem;
			height: 1.75rem;
			z-index: 300;
			border-radius: $borderRadius;
			box-shadow: var(--shadow-md);
		}
	}

	:deep(.region-select) {
		stroke: var(--contrast);
		stroke-width: 2;
		stroke-dasharray: 6 4;
		fill: $c3sgrey;
		fill-opacity: 0.08;
		cursor: default;
	}

	:deep(.close-region-marker) {
		background: none;
		border: none;

		.button {
			width: $buttonSize * 0.8;
			height: $buttonSize * 0.8;
			padding: 0;
			border-radius: $borderRadius;
			pointer-events: all;
			opacity: 0.8;
			background-color: var(--contrast);
		}
	}

	.zoom-control {
		transition: transform $transition;
		margin: $panelMargin;
		transform: translate(calc(0rem - 3 * $buttonSize - 4 * $panelMargin), 0);
		&.hidden {
			transform: translate(0rem - 3 * $buttonSize - 4 * $panelMargin, -200%);
		}
		.zoom-buttons {
			display: flex;
			flex-direction: row;
			gap: 0.5rem;
			z-index: 100;
			pointer-events: all;
		}

		.zoom-button {
			// width: 2.5rem;
			// height: 2.5rem;
			// padding: 0.5rem;
			// display: flex;
			// align-items: center;
			// justify-content: center;
			// svg {
			// 	width: 1.5rem;
			// 	height: 1.5rem;
			// }
			border-radius: 100%;
			width: 2.5rem;
			height: 2.5rem;
			padding: 0.5rem;
			z-index: 300;
			box-shadow: var(--shadow-md);

			&.hidden {
				transform: translateX(150%);
			}

			// border-radius: 0;
			// &:first-child {
			// 	border-top-left-radius: $borderRadius;
			// 	border-bottom-left-radius: $borderRadius;
			// }
			// &:last-child {
			// 	border-top-right-radius: $borderRadius;
			// 	border-bottom-right-radius: $borderRadius;
			// }
		}
	}

	:deep(.leaflet-control-scale) {
		transform: translate(-2px, 2px);
		margin: 0;
	}
	:deep(.leaflet-control-attribution),
	:deep(.leaflet-control-scale) {
		background: var(--panel-bg-alt);
		backdrop-filter: $frosty;

		div {
			background: transparent;
		}
	}

	:deep(.leaflet-top),
	:deep(.leaflet-bottom),
	:deep(.leaflet-left),
	:deep(.leaflet-right) {
		transition: padding $transition;
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
		transition: opacity $transition;
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
			backdrop-filter: blur(2px);

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
