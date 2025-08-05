import * as d3 from 'd3'
import { differenceInDays } from 'date-fns'
import { defineStore } from 'pinia'

type LayerDetails = any

interface Event {
	times: Date[]
	slices: any[]
	featureLevel?: number
	regions: any[]
	maxArea: number
	bbox: [number, number, number, number]
	centroid: [number, number]
	size: number
	feature: boolean
	ocean_only?: boolean // Whether the event is only in ocean regions
	id: number
}

export interface FullEvent {
	id: number
	times: Date[]
	regions: any[]
	slices: any[]
	values: any[]
	centroids: [[number, number]]
	bbox: [number, number, number, number]
	total_area: number
	areas: number[]
	peak_values: number[]
	mean_values: number[]
	color?: string
}

interface State {
	lang: Language
	loadingCount: number
	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: Event[]
	selectedEvent?: FullEvent | null

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
		includeOceanEvents : boolean
	}
	draggingFilter: boolean

	wrafRegion?: 'none' | 'wraf-01' | 'wraf-05' | 'wraf-2' | 'wraf-5' | 'wraf-10'
	regionsToSelectBy?: GeoJSON.FeatureCollection

}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'
// export const catScheme = [...d3.schemeDark2, ...d3.schemeCategory10]
const getColor = (i: number) => d3.interpolateWarm((i * 0.61803398875) % 1)
export const catScheme = Array.from({ length: 100 }, (_, i) => getColor(i))

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			selectedTime: new Date(Date.UTC(2024, 4, 28, 0, 0, 0)),
			layerDetails: null,
			// times: [],
			startTime: new Date(),
			endTime: new Date(),
			events: [],
			selectedEvent: null,

			lat2Index: d3.scaleLinear().domain([-90, 90]).range([0, 721]).clamp(true).unknown(-1).interpolate(() => t => Math.floor(t)),
			lon2Index: d3.scaleLinear().domain([-180, 180]).range([0, 1440]).clamp(true).unknown(-1).interpolate(() => t => Math.floor(t)),
			timePanelExpanded: false,
			timePanelVisible: true,
			selectedModel: undefined, // This can be set to a model name to load events from a specific model
			filtersExpanded: false,
			filters: {
				duration: 3,
				intensity: 0,
				size: 0, 
				includeOceanEvents: true, // Whether to include ocean events in the filter
			},
			draggingFilter: false,
			regionsToSelectBy: undefined, // This can be set to a GeoJSON FeatureCollection to select events by region
		}
	},
	getters: {
		eventSelected: (state) => {
			return state.selectedEvent !== null && state.selectedEvent !== undefined
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
		filteredEvents: (state) => {

			// Filter events based on the current filters
			const fe= state.events.filter((event) => {
				// Check if the event is an ocean event if the filter is enabled
				if (!state.filters.includeOceanEvents && event.ocean_only) {
					console.log('Skipping ocean event:', JSON.stringify(state.filters.includeOceanEvents))
					return false
				}
				// Check duration filter
				const duration = differenceInDays(event.times[event.times.length - 1], event.times[0])
				if (duration < state.filters.duration) {
					// console.log('Skipping short event:', event)
					return false
				}
				// Check intensity filter
				const intensity = event.intensity || 0 // Default to 0 if intensity is not defined
				if (intensity < state.filters.intensity) {
					console.log('Skipping weak event:', event)
					return false
				}
				// Check size filter
				const sizePercentile = event.size || 0
				if (sizePercentile < state.filters.size) {
					console.log('Skipping small event:', event)
					return false
				}
				// If all filters pass, include the event
				return true
			})
			console.log('Filtered events:', fe.length, 'from', state.events.length, 'total events')
			return fe
		},
		// Returns the events which are active at the selected time (i.e. plotted on the map)
		currentEvents: (state) => {
			return state.filteredEvents.filter((event) => {
				const startDate = new Date(event.times[0])
				const endDate = new Date(event.times[event.times.length - 1])
				startDate.setHours(0, 0, 0, 0)
				endDate.setHours(23, 59, 59, 999)
				return state.selectedTime >= startDate && state.selectedTime <= endDate
			})
		},
	},
	actions: {
		async selectEvent(id: number | null) {
			if (id === null) {
				this.selectedEvent = null
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
				const event = (await resp.json())
				// This should always be the case...
				event.id = id
				event.times = event.times.map((time: string) => new Date(time))
				event.color = catScheme[event.id % catScheme.length]
				this.selectedEvent = event as FullEvent
				if(this.selectedTime < event.times[0] || this.selectedTime > event.times[event.times.length - 1]) {
					this.selectedTime = new Date(event.times[0])
				}
				this.setLoadingDone()
			}
		},
		toggleTimePanel() {
			this.timePanelExpanded = !this.timePanelExpanded
		},
		toggleEventSelectedDebug() {
			this.selectedEvent =
				this.selectedEvent === null ? (new Object() as FullEvent) : null
		},
		setLoading() {
			this.loadingCount++
		},
		setLoadingDone() {
			this.loadingCount--
		},
		init() {
			this.setLoading()
			let path = `/events.jsonl`
			if(this.selectedModel) {
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

						event.color = catScheme[event.id % catScheme.length]
					})

					// this.events = data.filter((_, i) => i % 4 === 0) as Event[]
					this.events = data as Event[]
					console.log('Events loaded:', this.events)
					// this.events.forEach((event) => {
					// 	event.times = event.times.map((time: string) => new Date(time))

					// })
					this.setLoadingDone()
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
				})
		},
	},
})
