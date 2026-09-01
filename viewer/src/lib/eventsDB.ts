import FetchAndIndexWorker from '@/lib/worker/fetchAndIndexWorker?worker'
import { EventStore } from '@/store/eventStore'
import { useStore as useMainStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { bbox, booleanPointInPolygon, point } from '@turf/turf'
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
let _wetOn = true
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
const loadedYears = new Set<number>()

type FetchTask = { year: number; eventType: EventType; active?: boolean }
let _backgroundTasks: FetchTask[] = []
let _foregroundRemaining = 0

const fetchAndIndexWorker = new FetchAndIndexWorker()
fetchAndIndexWorker.onmessage = (
	e: MessageEvent<{
		year: number
		events: ExtremeEvent[]
		pixelIndex: Record<number, number[]>
		dateIndex: Record<number, number[]>
		monthIndex: Record<string, number[]>
		eventType: EventType
		active: boolean
	}>,
) => {
	retrievedCount++

	// Nothing is posted for the types the user cannot see until the ones they
	// can are all in, so anything arriving while the count is still running is
	// part of the visible wave. See fetchAndIndexEvents.
	if (_foregroundRemaining > 0 && --_foregroundRemaining === 0) {
		for (const task of _backgroundTasks) {
			fetchAndIndexWorker.postMessage(task)
		}
		_backgroundTasks = []
	}

	const {
		year,
		events,
		pixelIndex: pIndex,
		dateIndex: dIndex,
		monthIndex: mIndex,
		eventType,
		active,
	} = e.data

	// console.log(`Main thread received ${events.length} events from worker for year ${year}`)

	_events.push(...events)
	// Events still in progress don't belong to a year, so they mustn't be allowed
	// to make a year look loaded
	if (!active) loadedYears.add(year)

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

	const recentYearsLoaded =
		loadedYears.has(latestYear) &&
		loadedYears.has(latestYear - 1) &&
		loadedYears.has(latestYear - 2)

	if (recentYearsLoaded || retrievedCount === postedCount) {
		const mainStore = useMainStore()
		// mainStore.setLoading()
		for (const cb of globalEventsChangedTriggers) {
			cb()
		}
		if (eventType === 'hot' && (active || year === latestYear)) {
			const timeStore = useTimeStore()
			if (events.length > 0) {
				// Events in progress run past the end of the finished catalogue, and
				// aren't guaranteed to be in chronological order, so take the latest
				// time in the batch and only ever move forwards.
				let latestTime = 0
				for (const event of events) {
					const endTime = event.times[event.times.length - 1]
					if (endTime > latestTime) latestTime = endTime
				}
				if (latestTime > timeStore.selectedTime.getTime()) {
					timeStore.selectedTime = new Date(latestTime)
				}
			} 
			// TODO - Get the latest updated date
			timeStore.selectedTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
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
			// if(year === latestYear) {
			// 	mainStore.mainHelpOpen = true
			// }
			// mainStore.setLoadingDone()
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
 *
 * The types the user is actually looking at are fetched first, most recent
 * year first, and the rest only once those are in. All of it used to be posted
 * at once, which left the year the map opens on queued behind decades of
 * events for types that are not on screen.
 *
 * @param eventTypes every type to load
 * @param from earliest year
 * @param to latest year
 * @param visibleTypes the subset that is currently on screen; the rest load in
 *   the background
 */
export async function fetchAndIndexEvents(
	eventTypes: EventType[],
	from: number,
	to: number,
	visibleTypes: EventType[] = eventTypes,
) {
	postedCount = 0
	retrievedCount = 0
	latestYear = to
	loadedYears.clear()
	_backgroundTasks = []
	_foregroundRemaining = 0

	const years = Array.from(
		{ length: to - from + 1 },
		(_, i) => i + from,
	).reverse()

	const tasksFor = (types: EventType[]): FetchTask[] => {
		// Events still in progress, fetched first so the leading edge fills in
		// early. These are a snapshot taken at page load; a site refresh picks up
		// newer ones.
		const tasks: FetchTask[] = types.map((eventType) => ({
			year: to,
			eventType,
			active: true,
		}))
		for (const year of years) {
			for (const eventType of types) {
				tasks.push({ year, eventType })
			}
		}
		return tasks
	}

	const visible = eventTypes.filter((t) => visibleTypes.includes(t))
	const hidden = eventTypes.filter((t) => !visibleTypes.includes(t))

	// If nothing is marked visible there is no sensible order to prefer, so
	// fall back to loading everything at once as before.
	const foreground = tasksFor(visible.length ? visible : eventTypes)
	_backgroundTasks = visible.length ? tasksFor(hidden) : []

	// Counted across both waves, so that "everything has arrived" stays true
	// only when it has
	postedCount = foreground.length + _backgroundTasks.length
	_foregroundRemaining = foreground.length

	for (const task of foreground) {
		fetchAndIndexWorker.postMessage(task)
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
	// console.log('Set parameter filters', filters)
	buildParameterFilterResults()
}

export function setEventTypeFilter(hotOn: boolean, coldOn: boolean, wetOn: boolean) {
	_hotOn = hotOn
	_coldOn = coldOn
	_wetOn = wetOn
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
			const wIntenF = _parameterFilters!.wetIntensity
			if (wIntenF.active && event.event_type === 'wet') {
				const wetVal = event.mean_value
				if (wIntenF.minimum && wetVal < wIntenF.value) return false
				if (!wIntenF.minimum && wetVal > wIntenF.value) return false
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
		if (e.event_type === 'wet' && !_wetOn) return false
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

export function clearSpatialFilter(): ExtremeEvent[] {
	_pointFilter = null
	_regionFilter = null

	return buildSpatialFilterResults()
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
		// Use the feature directly so both Polygon and MultiPolygon are supported.
		const region = _regionFilter
		const bounds = bbox(region) as [number, number, number, number]

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
				if (booleanPointInPolygon(p, region)) {
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
	time: Date | null,
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
