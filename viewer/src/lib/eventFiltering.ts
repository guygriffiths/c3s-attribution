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
let resultReady = false
let counts: Map<number, Array<number>> = new Map()

const regionEventsReadyTriggers: Array<() => void> = []
const globalEventsReadyTriggers: Array<() => void> = []
const indexBuiltTriggers: Array<() => void> = []
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
	}
	pixelWorker.postMessage(events)

	const dateWorker = new DateWorker()
	dateWorker.onmessage = (e: MessageEvent<Record<string, number[]>>) => {
		dateIndex = e.data
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
	lastResult = (pixelIndex[packPixelToInt(lat, lon)] || []).map(
		(idx) => _filteredEvents[idx],
	)
	resultReady = true
	regionEventsReadyTriggers.forEach((cb) => cb())

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
	resultReady = true
	regionEventsReadyTriggers.forEach((cb) => cb())

	return lastResult
}

export function setPostFilters(filters: MainStore['filters']) {
	_filteredEvents = postFilterEvents(_events, filters)
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
): ExtremeEvent[] => {
	const fe = events.filter((event: ExtremeEvent, i) => {
		if (!filters.includeOceanEvents && event.ocean_only) return false

		if (event.duration < filters.duration) return false

		const intensity = event.peak_value || 0
		if (intensity < filters.intensity) return false

		const pixelCount = event.pixel_count || 0
		if (pixelCount < filters.size) return false

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
	return lastResult
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
	return result
}

export function getCurrentDayCounts(): Map<number, Array<number>> {
	return counts
}

export function getGlobalFilteredEvents(): ExtremeEvent[] {
	return _filteredEvents
}
