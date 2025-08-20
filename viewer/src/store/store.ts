import { filterEvents } from '@/lib/utils'
import { point, polygon } from '@turf/helpers'
import { booleanContains } from '@turf/turf'
import * as d3 from 'd3'
import { differenceInDays, getDayOfYear } from 'date-fns'
import Flatbush from 'flatbush'
import { MultiPolygon, Polygon } from 'geojson'
import { LatLng, Point } from 'leaflet'
import { defineStore } from 'pinia'
import { watch } from 'vue'

type LayerDetails = any
type ViewMode = 'explore' | 'heatmap'

interface State {
	lang: Language
	loadingCount: number
	viewMode: ViewMode
	mapCentre: Point

	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: ExtremeEvent[]

	selectedEvent: ExtremeEventFull | null

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
	filteredEvents: ExtremeEvent[]
	draggingFilter: boolean
	fastFilterEvents: ExtremeEvent[] // This is the set of events that are filtered by the fast filter for draggina and other UI interactions

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
			viewMode: 'heatmap',
			mapCentre: new LatLng(0, 0) as unknown as Point, // Default center point for the map

			selectedTime: new Date(Date.UTC(2020, 4, 28, 0, 0, 0)),
			layerDetails: null,
			// times: [],
			startTime: new Date(),
			endTime: new Date(),
			events: [],
			selectedEvent: null,

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
			fastFilterEvents: [], // This is the set of events that are filtered by the fast filter for dragging and other UI interactions
			wrafLevel: 'none',
			regionsToSelectBy: null, // Will store the loaded WRAF regions. The actual selected region is in filters.wrafRegion
			spatialIndex: null, // Spatial index for events, if needed
		}
	},
	getters: {
		eventSelected: (state) => {
			return state.selectedEvent !== null && state.selectedEvent !== undefined
		},
		exploringRegion: (state) => {
			return (
				!state.selectedEvent &&
				state.filters.wrafRegion !== null &&
				state.filters.wrafRegion !== undefined
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
			state.filteredEvents.forEach((event) => {
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
		getPointFilteredEvents(pointToFilter: [number, number]) {
			if (!this.spatialIndex) {
				console.warn('Spatial index not initialized, cannot filter by point')
				return []
			}

			const [lat, lon] = pointToFilter
			const p = point([lon, lat]) // Turf expects [x, y] = [lon, lat]

			// Query the index: Flatbush returns candidate IDs whose bbox intersects the point
			const candidateIds = this.spatialIndex.search(lat, lon, lat, lon).map((id) => this.events[id].id)
			const candidateSet = new Set(candidateIds)

			return this.filteredEvents.filter((event) => {
				if (!candidateSet.has(event.id)) return false
				const totalPoly = polygon([
					event.total_region.map(([lat, lon]) => [lon, lat]),
				])
				return booleanContains(totalPoly, p)
			})
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

						// normalize total_region longitudes to avoid IDL issues
						const lons = event.total_region.map(
							([_, lon]: [number, number]) => lon,
						)
						const maxLon = Math.max(...lons)
						const minLon = Math.min(...lons)

						if (maxLon - minLon > 180) {
							console.log('normalising', JSON.stringify(event.total_region))
							// crosses the dateline: shift any lon < 0 by +360
							event.total_region = event.total_region.map(
								([lat, lon]: [number, number]) => {
									const newLon = lon < 0 ? lon + 360 : lon
									return [lat, newLon]
								},
							)
							console.log('normalised', event.total_region)
						}
					})

					// this.events = data.filter((_, i) => i % 4 === 0) as Event[]
					this.events = data as ExtremeEvent[]
					console.log('Events loaded:', this.events)
					this.spatialIndex = new Flatbush(this.events.length, 2)
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
					// this.events.forEach((event) => {
					// 	event.times = event.times.map((time: string) => new Date(time))

					// })
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
