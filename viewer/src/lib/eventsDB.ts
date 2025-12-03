import FetchAndIndexWorker from '@/lib/worker/fetchAndIndexWorker?worker'
import { EventStore } from '@/store/eventStore'
import { useStore as useMainStore } from '@/store/store'
import { bbox, booleanPointInPolygon, point, polygon } from '@turf/turf'
import type { MultiPolygon, Polygon } from 'geojson'
import { nextTick } from 'vue'
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
let finalised = false

const regionEventsReadyTriggers: Array<() => void> = []
const globalEventsReadyTriggers: Array<() => void> = []
const currentEventTriggers: Array<() => void> = []
export function onRegionEventsReady(cb: () => void) {
	regionEventsReadyTriggers.push(cb)
	if (lastResult.length > 0) {
		cb()
	}
}
export function onGlobalEventsReady(cb: () => void) {
	// console.log('Registering global events ready callback', cb)
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

let retrievedCount = 0
let postedCount = 0
let latestYear = 0

const fetchAndIndexWorker = new FetchAndIndexWorker()
fetchAndIndexWorker.onmessage = (
	e: MessageEvent<{
		year: number
		events: ExtremeEvent[]
		pixelIndex: Record<number, number[]>
		dateIndex: Record<string, number[]>
	}>,
) => {
	retrievedCount++
	const { year, events, pixelIndex: pIndex, dateIndex: dIndex } = e.data

	// console.log(`Main thread received ${events.length} events from worker`)

	_events.push(...events)
	_filteredEvents = _events
	for (const event of events) {
		_filteredIds.add(event.id)
	}

	// Merge pixel index
	for (const [key, val] of Object.entries(pIndex)) {
		if (!pixelIndex[Number(key)]) pixelIndex[Number(key)] = []
		pixelIndex[Number(key)].push(...val)
	}
	// Merge date index
	for (const [key, val] of Object.entries(dIndex)) {
		if (dateIndex[key]) {
			dateIndex[key] = dateIndex[key].concat(val)
		} else {
			dateIndex[key] = val
		}
	}

	if (retrievedCount === postedCount) {
		globalEventsReady = true
		pixelIndexReady = true
		dateIndexReady = true
	}

	if (year === latestYear || retrievedCount === postedCount) {
		const mainStore = useMainStore()
		mainStore.setLoading()
		for (const cb of globalEventsReadyTriggers) {
			cb()
		}
		for (const cb of currentEventTriggers) {
			cb()
		}
		nextTick(async () => {
			await new Promise((resolve) => requestAnimationFrame(resolve))
			await new Promise((resolve) => requestAnimationFrame(resolve))
			mainStore.setLoadingDone()
		})
	}
	// console.log(
	// 	'Merged indexes, and called back callbacks, retrieved',
	// 	retrievedCount,
	// 	'of',
	// 	postedCount,
	// 	'Total events', _events.length,
	// )
}

/**
 * Initialise global store
 */
export async function fetchAndIndexEvents(
	prefixes: string[],
	from: number,
	to: number,
) {
	postedCount = 0
	retrievedCount = 0
	latestYear = to

	const years = Array.from(
		{ length: to - from + 1 },
		(_, i) => i + from,
	).reverse()

	for (const year of years) {
		for (const prefix of prefixes) {
			postedCount++
			fetchAndIndexWorker.postMessage({ year, prefix })
		}
	}
}

export function finaliseEventFilters() {
	if (finalised) return
	finalised = true
}

export function manualGlobalTrigger() {
	for (const cb of globalEventsReadyTriggers) {
		cb()
	}
}

export function manualDateTrigger() {
	for (const cb of currentEventTriggers) {
		cb()
	}
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

	if (coldOnly) {
		return lastResult.filter((e) => e.event_type === 'cold')
	}
	if (hotOnly) {
		return lastResult.filter((e) => e.event_type === 'hot')
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

	if (coldOnly) {
		return lastResult.filter((e) => e.event_type === 'cold')
	}
	if (hotOnly) {
		return lastResult.filter((e) => e.event_type === 'hot')
	}
	return lastResult
}

export function setPostFilters(
	filters: EventStore['filters'],
	durationGetter: (e: ExtremeEvent) => number = (e) => e.duration,
	intensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0,
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
	currentEventTriggers.forEach((cb) => cb())
}

const postFilterEvents = (
	events: ExtremeEvent[],
	filters: EventStore['filters'],
	durationGetter: (e: ExtremeEvent) => number = (e) => e.duration,
	heatIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0,
	coldIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0,
	sizeGetter: (e: ExtremeEvent) => number = (e) => e.total_area || 0,
): ExtremeEvent[] => {
	const fe = events.filter((event: ExtremeEvent, i) => {
		const durF = filters.duration
		if (durF.minimum && durationGetter(event) < durF.value) return false
		if (!durF.minimum && durationGetter(event) > durF.value) return false
		const hIntenF = filters.heatIntensity
		if (hIntenF.active && event.event_type === 'hot') {
			switch (hIntenF.type) {
				case 'intensity':
					// use intensityGetter
					break
				case 'min':
					heatIntensityGetter = (e) => e.min_value - 273.15
					break
				case 'mean':
					heatIntensityGetter = (e) => e.mean_value - 273.15
					break
				case 'max':
					heatIntensityGetter = (e) => e.max_value - 273.15
					break
			}
			if (hIntenF.minimum && heatIntensityGetter(event) < hIntenF.value)
				return false
			if (!hIntenF.minimum && heatIntensityGetter(event) > hIntenF.value)
				return false
		}
		const cIntenF = filters.coldIntensity
		if (cIntenF.active && event.event_type === 'cold') {
			switch (cIntenF.type) {
				case 'intensity':
					// use intensityGetter
					break
				case 'min':
					coldIntensityGetter = (e) => e.min_value - 273.15
					break
				case 'mean':
					coldIntensityGetter = (e) => e.mean_value - 273.15
					break
				case 'max':
					coldIntensityGetter = (e) => e.max_value - 273.15
					break
			}
			if (cIntenF.minimum && coldIntensityGetter(event) < cIntenF.value)
				return false
			if (!cIntenF.minimum && coldIntensityGetter(event) > cIntenF.value)
				return false
		}
		const sizeF = filters.size
		if (sizeF.minimum && sizeGetter(event) < sizeF.value) return false
		if (!sizeF.minimum && sizeGetter(event) > sizeF.value) return false

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
	if (coldOnly) {
		return lastResult.filter((e) => e.event_type === 'cold')
	}
	if (hotOnly) {
		return lastResult.filter((e) => e.event_type === 'hot')
	}
	return lastResult
}

export function getFilteredIds(): Set<string> {
	if (coldOnly) {
		return new Set(
			lastResult.filter((e) => e.event_type === 'cold').map((e) => e.id),
		)
	}
	if (hotOnly) {
		return new Set(
			lastResult.filter((e) => e.event_type === 'hot').map((e) => e.id),
		)
	}
	return lastIds
}

export function getCurrentEvents(time: Date): ExtremeEvent[] {
	if (!time) return _filteredEvents

	const idxs = dateIndex[time.getTime()]
	if (!idxs) return []

	const result: ExtremeEvent[] = []
	for (const idx of idxs) {
		const ev = _events[idx]
		if (_filteredIds.has(ev.id)) result.push(ev)
	}

	if (coldOnly) {
		return result.filter((e) => e.event_type === 'cold')
	}
	if (hotOnly) {
		return result.filter((e) => e.event_type === 'hot')
	}
	return result
}

export function getCurrentDayCounts(): Map<number, Array<number>> {
	return counts
}

export function getGlobalFilteredEvents(): ExtremeEvent[] {
	if (coldOnly) {
		return _filteredEvents.filter((e) => e.event_type === 'cold')
	}
	if (hotOnly) {
		return _filteredEvents.filter((e) => e.event_type === 'hot')
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
