// lib/eventsStore.ts
import DateWorker from '@/lib/worker/dateIndexWorker?worker'
import PixelWorker from '@/lib/worker/pixelIndexWorker?worker'
import { MainStore } from '@/store/store'
import { bbox, booleanPointInPolygon, point, polygon } from '@turf/turf'
import type { MultiPolygon, Polygon } from 'geojson'
import { packPixelToInt } from './utils'

let _events: ExtremeEvent[] = []
let _filteredEvents: ExtremeEvent[] = []
let _filteredIds: Set<string> = new Set()
let lastPointFilter: [number, number] | null = null
let lastRegionFilter: GeoJSON.Feature<Polygon | MultiPolygon> | null = null

let pixelIndex: Record<number, number[]> = {} // Maps packed pixel IDs to event IDs for fast lookup
let dateIndex: Record<string, number[]> = {}
let pixelIndexReady = false
let dateIndexReady = false
let globalEventsReady = false
let lastResult: ExtremeEvent[] = []
let lastIds: Set<string> = new Set()
let resultReady = false
let counts: Map<number, Array<number>> = new Map()

const regionEventsReadyTriggers: Array<() => void> = []
const globalEventsReadyTriggers: Array<() => void> = []
const indexBuiltTriggers: Array<() => void> = []
const currentEventTriggers: Array<() => void> = []
export function onRegionEventsReady(cb: () => void) {
	regionEventsReadyTriggers.push(cb)
	if (lastResult.length > 0) {
		cb()
	}
}
export function onGlobalEventsReady(cb: () => void) {
	globalEventsReadyTriggers.push(cb)
	if (globalEventsReady) {
		cb()
	}
}
export function onCurrentEventsReady(cb: () => void) {
	currentEventTriggers.push(cb)
	if (dateIndexReady) {
		cb()
	}
}
export function onFilterBuilt(cb: () => void) {
	indexBuiltTriggers.push(cb)
	if (pixelIndexReady) {
		cb()
	}
}

/**
 * Initialise global store
 */
export function buildEventFilters(events: ExtremeEvent[]) {
	pixelIndexReady = false
	_events = events
	_filteredEvents = events
	_filteredIds = new Set(events.map((e) => e.id))
	globalEventsReady = true
	for (const cb of globalEventsReadyTriggers) {
		cb()
	}
	const pixelWorker = new PixelWorker()
	pixelWorker.onmessage = (e: MessageEvent<Record<number, number[]>>) => {
		pixelIndex = e.data
		pixelIndexReady = true
		for (const cb of indexBuiltTriggers) {
			cb()
		}
		console.log('Event filters built')
	}
	pixelWorker.postMessage(events)

	const dateWorker = new DateWorker()
	dateWorker.onmessage = (e: MessageEvent<Record<string, number[]>>) => {
		dateIndex = e.data
		dateIndexReady = true
		for (const cb of currentEventTriggers) {
			cb()
		}
		console.log('Date filters built')
	}
	dateWorker.postMessage(events)
}

export function getEventCount(): number {
	return _filteredEvents.length
}

export function setFilterToPoint(lat: number, lon: number): ExtremeEvent[] {
	resultReady = false
	lastPointFilter = [lat, lon]
	lastRegionFilter = null
	lastResult = (pixelIndex[packPixelToInt(lat, lon)] || [])
		.map((idx) => _events[idx])
		.filter((e) => _filteredIds.has(e.id))
	// TODO Find out why this is occasionally undefined
	lastResult = lastResult.filter((e) => e) // filter out undefined
	lastIds = new Set(lastResult.map((e) => e.id))
	resultReady = true
	regionEventsReadyTriggers.forEach((cb) => cb())

	if(coldOnly) {
		return lastResult.filter(e => e.event_type === 'cold')
	}
	if(hotOnly) {
		return lastResult.filter(e => e.event_type === 'hot')
	}
	return lastResult
}

/**
 * Region lookup – return all events overlapping a GeoJSON region
 */
export function setFilterToRegion(
	region: GeoJSON.Feature<Polygon | MultiPolygon>,
): ExtremeEvent[] {
	resultReady = false
	lastRegionFilter = region
	lastPointFilter = null
	// Gather pixels overlappin region → union their event IDs
	const ids = new Set<number>()
	const geom = region.geometry
	const poly = polygon(geom.coordinates as number[][][]) // assume Polygon
	const bounds = bbox(poly) as [number, number, number, number]

	for (let lat = Math.floor(bounds[1] * 4) / 4; lat <= bounds[3]; lat += 0.25) {
		for (
			let lon = Math.floor(bounds[0] * 4) / 4;
			lon <= bounds[2];
			lon += 0.25
		) {
			const p = point([lon, lat])
			if (booleanPointInPolygon(p, poly)) {
				const packed = packPixelToInt(lat, lon)
				const evIds = pixelIndex[packed]
				if (evIds) {
					evIds.forEach((id) => ids.add(id))
				}
			}
		}
	}

	// // `ids` now contains all unique event IDs that intersect the polygon
	lastResult = Array.from(ids).map((idx) => _filteredEvents[idx])
	lastIds = new Set(lastResult.map((e) => e.id))
	resultReady = true
	regionEventsReadyTriggers.forEach((cb) => cb())

	if(coldOnly) {
		return lastResult.filter(e => e.event_type === 'cold')
	}
	if(hotOnly) {
		return lastResult.filter(e => e.event_type === 'hot')
	}
	return lastResult
}

export function setPostFilters(
	filters: MainStore['filters'],
	durationGetter: (e: ExtremeEvent) => number = (e) => e.duration,
	intensityGetter: (e: ExtremeEvent) => number = (e) => e.peak_value || 0,
	sizeGetter: (e: ExtremeEvent) => number = (e) => e.pixel_set.length || 0,
) {
	_filteredEvents = postFilterEvents(
		_events,
		filters,
		durationGetter,
		intensityGetter,
		sizeGetter,
	)
	_filteredIds = new Set(_filteredEvents.map((e) => e.id))
	if (lastPointFilter !== null) {
		setFilterToPoint(lastPointFilter[0], lastPointFilter[1])
	} else if (lastRegionFilter !== null) {
		setFilterToRegion(lastRegionFilter)
	}
	globalEventsReadyTriggers.forEach((cb) => cb())
}

const postFilterEvents = (
	events: ExtremeEvent[],
	filters: MainStore['filters'],
	durationGetter: (e: ExtremeEvent) => number = (e) => e.duration,
	intensityGetter: (e: ExtremeEvent) => number = (e) => e.peak_value || 0,
	sizeGetter: (e: ExtremeEvent) => number = (e) => e.pixel_set.length || 0,
): ExtremeEvent[] => {
	const fe = events.filter((event: ExtremeEvent, i) => {
		if (!filters.includeOceanEvents && event.ocean_only) return false

		if (durationGetter(event) < filters.duration) return false

		if (intensityGetter(event) < filters.intensity) return false

		if (sizeGetter(event) < filters.size) return false

		return true
	})

	return fe
}

export function pixelIndexInitialised(): boolean {
	return pixelIndexReady
}

export function filterResultReady(): boolean {
	return resultReady
}

export function restoreFilter() {
	resultReady = true
	regionEventsReadyTriggers.forEach((cb) => cb())
}

export function clearFilter() {
	resultReady = false
	regionEventsReadyTriggers.forEach((cb) => cb())
}

export function getFilteredEvents(): ExtremeEvent[] {
	if(coldOnly) {
		return lastResult.filter(e => e.event_type === 'cold')
	}
	if(hotOnly) {
		return lastResult.filter(e => e.event_type === 'hot')
	}
	return lastResult
}

export function getFilteredIds(): Set<string> {
	if(coldOnly) {
		return new Set(lastResult.filter(e => e.event_type === 'cold').map(e => e.id))
	}
	if(hotOnly) {
		return new Set(lastResult.filter(e => e.event_type === 'hot').map(e => e.id))
	}
	return lastIds
}

export function getCurrentEvents(time: Date): ExtremeEvent[] {
	if (!time) return _filteredEvents

	const key = time.toISOString().split('T')[0]
	const idxs = dateIndex[key]
	if (!idxs) return []

	const result: ExtremeEvent[] = []
	for (const idx of idxs) {
		const ev = _events[idx]
		if (_filteredIds.has(ev.id)) result.push(ev)
	}

	if(coldOnly) {
		return result.filter(e => e.event_type === 'cold')
	}
	if(hotOnly) {
		return result.filter(e => e.event_type === 'hot')
	}
	return result
}

export function getCurrentDayCounts(): Map<number, Array<number>> {
	return counts
}

export function getGlobalFilteredEvents(): ExtremeEvent[] {
	if(coldOnly) {
		return _filteredEvents.filter(e => e.event_type === 'cold')
	}
	if(hotOnly) {
		return _filteredEvents.filter(e => e.event_type === 'hot')
	}
	return _filteredEvents
}

let coldOnly = false
let hotOnly = false
export function setColdOnly() {
	if (coldOnly) return
	coldOnly = true
	hotOnly = false
	regionEventsReadyTriggers.forEach((cb) => cb())
	globalEventsReadyTriggers.forEach((cb) => cb())
	currentEventTriggers.forEach((cb) => cb())
}

export function setHotOnly() {
	if (hotOnly) return
	hotOnly = true
	coldOnly = false
}

export function setHotColdBoth() {
	if (!hotOnly && !coldOnly) return
	hotOnly = false
	coldOnly = false
}
