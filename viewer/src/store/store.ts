import { createEventFilterWorker } from '@/lib/eventFilterWorkerFactory'
import { filterEvents } from '@/lib/utils'
import { booleanContains, point, polygon } from '@turf/turf'
import * as d3 from 'd3'
import { differenceInDays, getDayOfYear } from 'date-fns'
import Flatbush from 'flatbush'
import { MultiPolygon, Polygon } from 'geojson'
import { LatLng, Point } from 'leaflet'
import { defineStore } from 'pinia'
import { watch } from 'vue'

const worker = createEventFilterWorker()

type LayerDetails = any
type ViewMode = 'explore' | 'heatmap'

interface State {
	lang: Language
	loadingCount: number
	viewMode: ViewMode
	mapCentre: Point
	// This holds a reference to a window through a panel through which the map is viewed
	// So we want to fit to these bounds, centre our zoom events here, etc.
	mapPeephole: HTMLElement | null

	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: ExtremeEvent[]
	showBars: boolean // Whether to show the bars in the time reel

	selectedEvent: ExtremeEventFull | null
	hoveringEventId: string | null

	lat2Index?: (lat: number) => number
	lon2Index?: (lon: number) => number
	// TODO Split into a separate UI store?
	selectedModel?: string

	timePanelVisible: boolean
	timePanelExpanded: boolean
	filtersExpanded: boolean
	filters: {
		duration: number
		intensity: number
		size: number
		includeOceanEvents: boolean
		wrafRegion: GeoJSON.Feature<Polygon | MultiPolygon> | null
	}
	// We don't want to trigger a full filter run on every point selection, so this is a separate filter
	selectedPointFilter: [number, number] | null
	lastPoint: [number, number] | null // This is used to store the last point selected on the map for filtering
	drawingRegion: boolean // Whether we are currently drawing a region on the map

	filteredEvents: ExtremeEvent[]
	draggingFilter: boolean
	regionFilteredEvents: ExtremeEvent[] // This is the set of events that are filtered by the fast filter for draggina and other UI interactions

	wrafLevel: 'none' | 'wraf-01' | 'wraf-05' | 'wraf-2' | 'wraf-5' | 'wraf-10'
	// This is the set of regions to select events by, if any
	// Corresponds to the WRAF level selected
	regionsToSelectBy: GeoJSON.FeatureCollection | null
	spatialIndex: Flatbush | null // Spatial index for events, if needed
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'

const rotateScheme = (i: number) => d3.interpolateWarm((i * 0.61803398875) % 1)
export const catScheme = Array.from({ length: 100 }, (_, i) => rotateScheme(i))

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			viewMode: 'heatmap', // 'explore' or 'heatmap'
			mapCentre: new LatLng(0, 0) as unknown as Point, // Default center point for the map
			mapPeephole: null, // This will be set to the map container element when the map is initialized

			selectedTime: new Date(Date.UTC(1981, 4, 28, 0, 0, 0)),
			layerDetails: null,
			// times: [],
			startTime: new Date(1979, 0, 1),
			endTime: new Date(),
			events: [],
			selectedEvent: null,
			showBars: false, // Whether to show the bars in the time reel
			hoveringEventId: null,

			lat2Index: d3
				.scaleLinear()
				.domain([-90, 90])
				.range([0, 721])
				.clamp(true)
				.unknown(-1)
				.interpolate(() => (t) => Math.floor(t)),
			lon2Index: d3
				.scaleLinear()
				.domain([-180, 180])
				.range([0, 1440])
				.clamp(true)
				.unknown(-1)
				.interpolate(() => (t) => Math.floor(t)),
			timePanelExpanded: false,
			timePanelVisible: true,
			selectedModel: undefined, // This can be set to a model name to load events from a specific model
			filtersExpanded: false,
			filters: {
				duration: 3,
				intensity: 0,
				size: 0,
				includeOceanEvents: true, // Whether to include ocean events in the filter
				wrafRegion: null, // This can be set to a WRAF region name to filter events by region
			},
			selectedPointFilter: null, // This is used to store a point selected on the map for filtering
			filteredEvents: [],
			draggingFilter: false,
			lastPoint: null,
			drawingRegion: false, // Whether we are currently drawing a region on the map
			regionFilteredEvents: [], // This is the set of events that are filtered by region on top of the main filters. This needs to be fast enough to live-render while dragging the point. It also must be 100% pixel accurate, as it is the main filter for region exploration.
			wrafLevel: 'none',
			regionsToSelectBy: null, // Will store the loaded WRAF regions. The actual selected region is in filters.wrafRegion
			spatialIndex: null, // Spatial index for events, if needed
		}
	},
	getters: {
		isFocused: (state) => {
			return (
				state.selectedEvent !== null ||
				state.filters.wrafRegion !== null ||
				(state.selectedPointFilter !== null && !state.draggingFilter)
			)
		},
		eventSelected: (state) => {
			return state.selectedEvent !== null && state.selectedEvent !== undefined
		},
		exploringRegion: (state) => {
			return (
				!state.selectedEvent &&
				((state.filters.wrafRegion !== null &&
					state.filters.wrafRegion !== undefined) ||
					state.selectedPointFilter !== null)
			)
		},
		isLoading: (state) => state.loadingCount > 0,
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
		selectedTimeIndex: (state) => {
			// Find the index of the selected time in the times array
			return differenceInDays(state.selectedTime, state.startTime)
		},
		// Returns the (filtered) events which are active at the selected time (i.e. plotted on the map)
		// TODO make it respond to a range, and use this is region explore
		currentEvents: (state: State) => {
			if (state.viewMode === 'heatmap') {
				console.log('Heatmap mode, returning all filtered events')
				return state.filteredEvents
			}
			// @ts-ignore
			return state.filteredEvents.filter((event: ExtremeEvent) => {
				const startDate = new Date(event.times[0])
				const endDate = new Date(event.times[event.times.length - 1])
				startDate.setHours(0, 0, 0, 0)
				endDate.setHours(23, 59, 59, 999)
				return state.selectedTime >= startDate && state.selectedTime <= endDate
			})
		},
		dayCounts: (state) => {
			// Create a map of day counts for each month
			const counts = new Map<number, Array<number>>()

			const iEvents = state.selectedPointFilter
				? state.regionFilteredEvents
				: state.filteredEvents

			iEvents.forEach((event) => {
				event.times.forEach((time) => {
					const year = time.getUTCFullYear()
					const day = getDayOfYear(time)
					if (!counts.has(year)) {
						counts.set(year, Array(366).fill(0))
					}
					counts.get(year)![day - 1]++
				})
			})
			for (
				let year = state.startTime.getUTCFullYear();
				year <= state.endTime.getUTCFullYear();
				year++
			) {
				if (!counts.has(year)) {
					counts.set(year, Array(366).fill(0))
				}
			}
			return counts
		},
	},
	actions: {
		async selectEvent(id: string | null) {
			if (id === null) {
				this.selectedEvent = null
				return
			}
			if (this.selectedEvent?.id === id) {
				this.selectedEvent = null
			} else {
				this.setLoading()
				let path = `/events/event-${id}.json`
				if (this.selectedModel) {
					path = `/data/output-debug-${this.selectedModel}/events/event-${id}.json`
				}
				const resp = await fetch(path)
				const event = await resp.json()
				// This should always be the case...
				event.id = id
				event.times = event.times.map((time: string) => new Date(time))
				event.duration =
					1 +
					differenceInDays(event.times[event.times.length - 1], event.times[0])
				event.color = catScheme[event.id % catScheme.length]
				this.selectedEvent = event as ExtremeEventFull
				if (
					this.selectedTime < event.times[0] ||
					this.selectedTime > event.times[event.times.length - 1]
				) {
					this.selectedTime = new Date(event.times[0])
				}
				this.setLoadingDone()
			}
		},
		async selectRegion(region: GeoJSON.Feature<Polygon | MultiPolygon> | null) {
			if (region === null) {
				this.filters.wrafRegion = null
			} else {
				this.filters.wrafRegion = region
			}
		},
		stopExploringRegion() {
			if (this.selectedPointFilter !== null) {
				this.selectedPointFilter = null
			} else if (this.filters.wrafRegion !== null) {
				this.filters.wrafRegion = null
			}
		},
		toggleTimePanel() {
			this.timePanelExpanded = !this.timePanelExpanded
		},
		toggleEventSelectedDebug() {
			this.selectedEvent =
				this.selectedEvent === null ? (new Object() as ExtremeEventFull) : null
		},
		async setLoading() {
			this.loadingCount++
			// Triggers Vue to re-render the map
			await new Promise((resolve) => setTimeout(resolve, 0))
		},
		setLoadingDone() {
			this.loadingCount--
		},
		getPointFilteredEvents(lat: number, lon: number) {
			if (!this.spatialIndex || !this.selectedPointFilter) {
				console.warn('Spatial index not initialized, cannot filter by point')
				return []
			}
			// Full filter in worker if this
			// worker.filter(this.selectedPointFilter!).then((result) => {
			// 	this.regionFilteredEvents = (result as number[]).map(
			// 		(idx) => this.events[idx],
			// 	)
			// })
			// console.time('fast filter')

			const candidateIds = this.spatialIndex.search(lat, lon, lat, lon)
			const candidateSet = new Set(candidateIds.map((id) => this.events[id].id))

			const fEvents = new Array<ExtremeEvent>(candidateIds.length)
			for (let i = 0; i < candidateIds.length; i++) {
				fEvents[i] = this.events[candidateIds[i]]
			}

			const p = point([lon, lat]) // Turf expects [x, y] = [lon, lat]
			this.regionFilteredEvents = fEvents.filter((event) => {
				// return true
				const totalPoly = polygon([
					event.total_region.map(([lat, lon]) => [lon, lat]),
				])
				return booleanContains(totalPoly, p)
			})
		},
		fixPointFilteredEvents() {
			// This is called when the user stops dragging the point filter
			// We want to do a full filter of the events now
			console.log(
				'Fixing point filtered events. This is disabled because it slows things down too much',
			)
			// this.filteredEvents = this.regionFilteredEvents
			// this.regionFilteredEvents = []
		},
		init() {
			this.setLoading()
			let path = `/events.jsonl`
			if (this.selectedModel) {
				// DEBUG - Can be removed later
				console.log('Loading events for model:', this.selectedModel)
				path = `/data/output-debug-${this.selectedModel}/events.jsonl`
			}

			fetch(path)
				.then((response) => {
					if (!response.ok) {
						throw new Error('Network response was not ok')
					}
					return response.text()
				})
				.then((text) => {
					const lines = text.trim().split('\n')
					const objects = lines.map((line) => JSON.parse(line))
					return objects
				})
				.then((data) => {
					this.startTime = new Date(9999, 0, 1)
					this.endTime = new Date(0)
					let col = 0
					data.forEach((event: any) => {
						// console.log('Processing event:', event)
						event.times = event.times.map((time: string) => new Date(time))
						const startDate = new Date(event.times[0])
						if (startDate < this.startTime) {
							this.startTime = new Date(startDate)
						}
						startDate.setHours(0, 0, 0, 0)
						const endDate = new Date(event.times[event.times.length - 1])
						if (endDate > this.endTime) {
							this.endTime = new Date(endDate)
						}
						endDate.setHours(23, 59, 59, 999)

						event.times.forEach((time: Date) => {
							const year = time.getUTCFullYear()
							const dayOfYear = getDayOfYear(time)
						})
						event.color = catScheme[col++ % catScheme.length]
						event.duration =
							1 +
							differenceInDays(
								event.times[event.times.length - 1],
								event.times[0],
							)

						// normalize total_region longitudes to avoid IDL issues
						const lons = event.total_region.map(
							([_, lon]: [number, number]) => lon,
						)
						const maxLon = Math.max(...lons)
						const minLon = Math.min(...lons)

						if (maxLon - minLon > 180) {
							// console.log('normalising', JSON.stringify(event.total_region))
							// crosses the dateline: shift any lon < 0 by +360
							event.total_region = event.total_region.map(
								([lat, lon]: [number, number]) => {
									const newLon = lon < 0 ? lon + 360 : lon
									return [lat, newLon]
								},
							)
							// console.log('normalised', event.total_region)
						}
					})

					// this.events = data.filter((_, i) => i % 4 === 0) as Event[]
					this.events = data as ExtremeEvent[]
					console.log('Events loaded:', this.events)
					this.spatialIndex = new Flatbush(this.events.length)
					this.events.forEach((event, i) => {
						const bbox = event.bbox
						if (bbox) {
							// Add the bounding box to the spatial index
							this.spatialIndex!.add(
								bbox[0], // minX
								bbox[1], // minY
								bbox[2], // maxX
								bbox[3], // maxY
							)
						} else {
							console.warn(
								`Event ${event.id} has no bounding box, skipping index addition`,
							)
						}
					})
					this.spatialIndex!.finish()
					console.log('Spatial index created for events:', this.spatialIndex)

					worker.init(this.events)

					this.setLoadingDone()
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
				})
			this.runFilters()
			watch(
				() => [this.filters, this.events, this.spatialIndex],

				this.runFilters,
				{ deep: true, immediate: true },
			)
		},
		async runFilters() {
			this.setLoading()

			this.filteredEvents = filterEvents(
				this.events,
				this.filters,
				this.spatialIndex,
				false,
			)

			// Full filter in worker if this gets too slow
			// But at the moment, it's the canvas update and Vue/Leafet rendering that is slow
			//
			// const result = await worker.send({
			// 	events: this.filteredEvents,
			// 	filters: this.filters,
			// 	spatialIndex: this.spatialIndex,
			// })

			this.filteredEvents = filterEvents(
				this.filteredEvents,
				this.filters,
				this.spatialIndex,
				true,
			)
			// This needs to get set by the leaflet layers
			this.setLoadingDone()
		},
	},
})

export type MainStore = ReturnType<typeof useStore>
