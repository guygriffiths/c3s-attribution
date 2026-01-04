import FetchAndIndexWorker from '@/lib/worker/fetchAndIndexWorker?worker'
import { EventStore } from '@/store/eventStore'
import { useStore as useMainStore } from '@/store/store'
import { bbox, booleanPointInPolygon, point, polygon } from '@turf/turf'
import type { MultiPolygon, Polygon } from 'geojson'
import { nextTick } from 'vue'
import { packPixelToInt } from './utils'

/**
 * Event indexing and filtering.
 * The filtering chain is as follows:
 *
 * _events: all events loaded
 * _parameterFilterEvents: events after applying parameter filters (duration, intensity, size, hot/cold event type)
 * _spatiallyFilteredEvents: events after applying spatial filters (point, region) to parameter filtered events
 * _fullyFilteredEvents: events after applying time filter to spatially and parameter filtered events
 *
 * Each of these is cached in variables, and updated when filters above it in the chain change.
 *
 * Some have a corresponding Set of IDs for fast lookup during downstream filtering.
 *
 */

let _events: ExtremeEvent[] = []
export const getAllEvents = (): ExtremeEvent[] => _events

let _parameterFilterEvents: ExtremeEvent[] = []
let _parameterFilterEventIds: Set<string> = new Set()
export const getParameterFilteredEvents = (): ExtremeEvent[] =>
	_parameterFilterEvents

let _spatiallyFilteredEvents: ExtremeEvent[] = []
let _spatiallyFilteredEventIds: Set<string> = new Set()
export const getSpatiallyFilteredEvents = (): ExtremeEvent[] =>
	_spatiallyFilteredEvents

let _timeFilteredEvents: ExtremeEvent[] = []
let _timeFilteredEventIds: Set<string> = new Set()
export const getTimeFilteredEvents = (): ExtremeEvent[] => _timeFilteredEvents

let _spaceTimeFilteredEvents: ExtremeEvent[] = []
export const getSpaceTimeFilteredEvents = (): ExtremeEvent[] =>
	_spaceTimeFilteredEvents

let _parameterFilters: EventStore['filters'] | null = null
let _hotOn = true
let _coldOn = true
let _pointFilter: [number, number] | null = null
let _regionFilter: GeoJSON.Feature<Polygon | MultiPolygon> | null = null
let _timeFilter: { start: Date; end: Date } | null = null

let _durationGetter: (e: ExtremeEvent) => number = (e) => e.duration
let _heatIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0
let _coldIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0
let _sizeGetter: (e: ExtremeEvent) => number = (e) => e.total_area || 0

let pixelIndex: Record<number, number[]> = {} // Maps packed pixel IDs to event IDs for fast lookup
let dateIndex: Record<string, number[]> = {}
let monthIndex: Record<string, number[]> = {}
let pixelIndexReady = false

let dateIndexReady = false
let globalEventsReady = false

const globalEventsChangedTriggers: Array<() => void> = []
const parameterFilterChangedTriggers: Array<() => void> = []
const spatialFilterChangedTriggers: Array<() => void> = []
const timeFilterChangedTriggers: Array<() => void> = []
const spaceTimeFilterChangedTriggers: Array<() => void> = []

export function onGlobalEventsChanged(cb: () => void) {
	globalEventsChangedTriggers.push(cb)
}
export function onParameterFilterChanged(cb: () => void) {
	parameterFilterChangedTriggers.push(cb)
}
export function onSpatialFilterChanged(cb: () => void) {
	spatialFilterChangedTriggers.push(cb)
}
export function onTimeFilterChanged(cb: () => void) {
	timeFilterChangedTriggers.push(cb)
}
export function onSpaceTimeFilterChanged(cb: () => void) {
	spaceTimeFilterChangedTriggers.push(cb)
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
		dateIndex: Record<number, number[]>
		monthIndex: Record<string, number[]>
	}>,
) => {
	retrievedCount++
	const {
		year,
		events,
		pixelIndex: pIndex,
		dateIndex: dIndex,
		monthIndex: mIndex,
	} = e.data

	// console.log(`Main thread received ${events.length} events from worker`)

	_events.push(...events)

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

	// Merge month index
	for (const [key, val] of Object.entries(mIndex)) {
		if (monthIndex[key]) {
			monthIndex[key] = monthIndex[key].concat(val)
		} else {
			monthIndex[key] = val
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
		for (const cb of globalEventsChangedTriggers) {
			cb()
		}
		// Trigger a build of the entire filter chain
		//
		// This starts with parameter filters, which triggers spatial filter rebuild,
		// which in turn triggers time filter rebuild
		//
		// Each stage notifies its own listeners when done
		//
		// This will populate all the filtered event arrays
		buildParameterFilterResults()

		nextTick(async () => {
			await new Promise((resolve) => requestAnimationFrame(resolve))
			await new Promise((resolve) => requestAnimationFrame(resolve))
			if(year === latestYear) {
				mainStore.mainHelpOpen = true
			}
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

export function pixelIndexInitialised(): boolean {
	return pixelIndexReady
}

export function setParameterFilters(
	filters: EventStore['filters'],
	durationGetter: (e: ExtremeEvent) => number = (e) => e.duration,
	heatIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0,
	coldIntensityGetter: (e: ExtremeEvent) => number = (e) => e.max_value || 0,
	sizeGetter: (e: ExtremeEvent) => number = (e) => e.total_area || 0,
) {
	_parameterFilters = filters
	_durationGetter = durationGetter
	_heatIntensityGetter = heatIntensityGetter
	_coldIntensityGetter = coldIntensityGetter
	_sizeGetter = sizeGetter
	buildParameterFilterResults()
}

export function setEventTypeFilter(hotOn: boolean, coldOn: boolean) {
	_hotOn = hotOn
	_coldOn = coldOn
	buildParameterFilterResults()
}

const buildParameterFilterResults = (): ExtremeEvent[] => {
	if (!_parameterFilters) {
		_parameterFilterEvents = _events
	} else {
		_parameterFilterEvents = _events.filter((event: ExtremeEvent, i) => {
			const durF = _parameterFilters!.duration
			if (durF.minimum && _durationGetter(event) < durF.value) return false
			if (!durF.minimum && _durationGetter(event) > durF.value) return false
			const hIntenF = _parameterFilters!.heatIntensity
			if (hIntenF.active && event.event_type === 'hot') {
				switch (hIntenF.type) {
					case 'intensity':
						// use intensityGetter
						break
					case 'min':
						_heatIntensityGetter = (e) => e.min_value - 273.15
						break
					case 'mean':
						_heatIntensityGetter = (e) => e.mean_value - 273.15
						break
					case 'max':
						_heatIntensityGetter = (e) => e.max_value - 273.15
						break
				}
				if (hIntenF.minimum && _heatIntensityGetter(event) < hIntenF.value)
					return false
				if (!hIntenF.minimum && _heatIntensityGetter(event) > hIntenF.value)
					return false
			}
			const cIntenF = _parameterFilters!.coldIntensity
			if (cIntenF.active && event.event_type === 'cold') {
				switch (cIntenF.type) {
					case 'intensity':
						// use intensityGetter
						break
					case 'min':
						_coldIntensityGetter = (e) => e.min_value - 273.15
						break
					case 'mean':
						_coldIntensityGetter = (e) => e.mean_value - 273.15
						break
					case 'max':
						_coldIntensityGetter = (e) => e.max_value - 273.15
						break
				}
				if (cIntenF.minimum && _coldIntensityGetter(event) < cIntenF.value)
					return false
				if (!cIntenF.minimum && _coldIntensityGetter(event) > cIntenF.value)
					return false
			}
			const sizeF = _parameterFilters!.size
			if (sizeF.minimum && _sizeGetter(event) < sizeF.value) return false
			if (!sizeF.minimum && _sizeGetter(event) > sizeF.value) return false

			return true
		})
	}
	_parameterFilterEvents = _parameterFilterEvents.filter((e) => {
		if (e.event_type === 'hot' && !_hotOn) return false
		if (e.event_type === 'cold' && !_coldOn) return false
		return true
	})
	_parameterFilterEventIds = new Set(_parameterFilterEvents.map((e) => e.id))

	// Notify listeners
	parameterFilterChangedTriggers.forEach((cb) => cb())
	// The parameter filter has changed, so downstream filters need to be rebuilt
	buildSpatialFilterResults()
	buildTimeFilterResults()
	return _parameterFilterEvents
}

export function setFilterToPoint(lat: number, lon: number): ExtremeEvent[] {
	_pointFilter = [lat, lon]
	_regionFilter = null

	return buildSpatialFilterResults()
}

export function setFilterToRegion(
	region: GeoJSON.Feature<Polygon | MultiPolygon>,
): ExtremeEvent[] {
	_regionFilter = region
	_pointFilter = null

	return buildSpatialFilterResults()
}

const buildSpatialFilterResults = (): ExtremeEvent[] => {
	if (_pointFilter) {
		const lat = _pointFilter![0]
		const lon = _pointFilter![1]
		const packed = packPixelToInt(lat, lon)
		const evIdxs = pixelIndex[packed]
		if (!evIdxs) {
			_spatiallyFilteredEvents = []
		} else {
			_spatiallyFilteredEvents = _events.filter((e, idx) => {
				if (evIdxs.includes(idx) && _parameterFilterEventIds.has(e.id)) {
					return true
				}
				return false
			})
		}
	} else if (_regionFilter) {
		// Gather pixels overlappin region → union their event IDs
		const evIdxs = new Set<number>()
		const geom = _regionFilter.geometry
		// TODO This assumes Polygon, need to handle MultiPolygon
		const poly = polygon(geom.coordinates as number[][][])
		const bounds = bbox(poly) as [number, number, number, number]

		for (
			let lat = Math.floor(bounds[1] * 4) / 4;
			lat <= bounds[3];
			lat += 0.25
		) {
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
						evIds.forEach((idx) => evIdxs.add(idx))
					}
				}
			}
		}

		_spatiallyFilteredEvents = _events.filter((e, idx) => {
			if (evIdxs.has(idx) && _parameterFilterEventIds.has(e.id)) {
				return true
			}
			return false
		})
	} else {
		_spatiallyFilteredEvents = _parameterFilterEvents
	}
	_spatiallyFilteredEventIds = new Set(
		_spatiallyFilteredEvents.map((e) => e.id),
	)

	// Notify listeners
	spatialFilterChangedTriggers.forEach((cb) => cb())
	// The spatial filter has changed, so downstream filters need to be rebuilt
	buildSpaceTimeFilterResults()
	return _spatiallyFilteredEvents
}

export function setTimeRangeFilter(start: Date, end: Date): ExtremeEvent[] {
	_timeFilter = { start, end }
	return buildTimeFilterResults()
}

const buildTimeFilterResults = (): ExtremeEvent[] => {
	if (_timeFilter) {
		const startTime = _timeFilter.start.getTime()
		const endTime = _timeFilter.end.getTime()

		_timeFilteredEvents = _parameterFilterEvents.filter((e) => {
			const eventStart = e.times[0]
			const eventEnd = e.times[e.times.length - 1]
			if (eventEnd < startTime || eventStart > endTime) {
				return false
			}
			return true
		})
	} else {
		_timeFilteredEvents = _parameterFilterEvents
	}
	_timeFilteredEventIds = new Set(_timeFilteredEvents.map((e) => e.id))

	// Notify listeners
	timeFilterChangedTriggers.forEach((cb) => cb())
	// The time filter has changed, so downstream filters need to be rebuilt
	buildSpaceTimeFilterResults()
	return _timeFilteredEvents
}

const buildSpaceTimeFilterResults = (): ExtremeEvent[] => {
	_spaceTimeFilteredEvents = _spatiallyFilteredEvents.filter((e) =>
		_timeFilteredEventIds.has(e.id),
	)
	// Notify listeners
	spaceTimeFilterChangedTriggers.forEach((cb) => cb())
	return _spaceTimeFilteredEvents
}

export function getCurrentEvents(
	time: Date,
	spatiallyFiltered: boolean,
): ExtremeEvent[] {
	if (!time) {
		if (spatiallyFiltered) {
			return _spatiallyFilteredEvents
		} else {
			return _parameterFilterEvents
		}
	}

	const idxs = dateIndex[time.getTime()]
	if (!idxs) return []

	const result: ExtremeEvent[] = []
	for (const idx of idxs) {
		const ev = _events[idx]
		if (spatiallyFiltered) {
			if (_spatiallyFilteredEventIds.has(ev.id)) result.push(ev)
		} else {
			if (_parameterFilterEventIds.has(ev.id)) result.push(ev)
		}
	}
	return result
}
