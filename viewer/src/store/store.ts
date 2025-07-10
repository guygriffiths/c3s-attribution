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
	id: number
}

interface FullEvent {
	times: Date[]
	slices: any[]
	featureLevel?: number
	regions: any[]
	maxArea: number
	bbox: [number, number, number, number]
	centroid: [number, number]
	size: number
	feature: boolean
	id: number
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

	timePanelExpanded: boolean

	selectedModel?: string
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
			timePanelExpanded: true,
			selectedModel: 'RAD5-DBSCANFalse-THRESH301.15-PERC98'
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
		// Returns the events which are active at the selected time (i.e. plotted on the map)
		activeEvents: (state) => {
			return state.events.filter((event) => {
				const startDate = new Date(event.times[0])
				const endDate = new Date(event.times[event.times.length - 1])
				startDate.setHours(0, 0, 0, 0)
				endDate.setHours(23, 59, 59, 999)
				return state.selectedTime >= startDate && state.selectedTime <= endDate
			})
		},
	},
	actions: {
		async selectEvent(id: number) {
			console.log('Selecting event with id:', id, this.selectedEvent)
			if (this.selectedEvent?.id === id) {
				this.selectedEvent = null
			} else {
				this.setLoading()
				let path = `/events/event-${id}.json`
				if (this.selectedModel !== undefined) {
					path = `/data/output-debug-${this.selectedModel}/events/event-${id}.json`
				}
				const resp = await fetch(path)
				const event = (await resp.json())
				// This should always be the case...
				event.id = id
				event.times = event.times.map((time: string) => new Date(time))
				event.color = catScheme[event.id % catScheme.length]
				this.selectedEvent = event as FullEvent
				this.timePanelExpanded = true
				this.setLoadingDone()
			}
		},
		toggleTimePanel() {
			this.timePanelExpanded = !this.timePanelExpanded
		},
		toggleEventSelectedDebug() {
			this.selectedEvent =
				this.selectedEvent === null ? (new Object() as Event) : null
		},
		setLoading() {
			this.loadingCount++
		},
		setLoadingDone() {
			this.loadingCount--
		},
		init() {
			this.setLoading()
			let path = `/events/events.jsonl`
			if(this.selectedModel !== undefined) {
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
