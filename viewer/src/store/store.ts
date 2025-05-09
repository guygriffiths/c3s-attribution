import * as d3 from 'd3'
import { addDays, format } from 'date-fns'
import { defineStore } from 'pinia'

type LayerDetails = any

interface Event {
	times: string[]
	startTime: Date
	endTime: Date
	slices: any[]
	maxArea: number
	bbox: [number, number, number, number]
	centroid: [number, number]
	size: number
}

interface State {
	lang: Language
	loadingCount: number
	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: any[]
	eventsByDay: Map<string, Event[]>
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'
export const catScheme = [...d3.schemePaired, ...d3.schemeSet3]

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			selectedTime: new Date(2024, 4, 28, 0, 0, 0),
			layerDetails: null,
			// times: [],
			startTime: new Date(),
			endTime: new Date(),
			events: [],
			eventsByDay: new Map(),
		}
	},
	getters: {
		isLoading: (state) => state.loadingCount > 0,
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
		activeEvents: (state) => {
			return state.events.filter((event) => {
				const startDate = new Date(event.startTime)
				const endDate = new Date(event.endTime)
				startDate.setHours(0, 0, 0, 0)
				endDate.setHours(23, 59, 59, 999)
				return (
					state.selectedTime >= startDate &&
					state.selectedTime <= endDate
				)
			})
			// Once events support this...
			// const dateStr = format(state.selectedTime, 'yyyy-MM-dd')
			// state.eventsByDay.get(dateStr)?.map((event) => {
			// 	const idx = event.times.indexOf(state.selectedTime.toISOString())
			// 	const points = event.slices[idx].map(
			// 		(slice: [number, number, number]) => turfPoint([slice[1], slice[2]]),
			// 	)
			// 	// Create a FeatureCollection
			// 	const featureCollection = turfFeatureCollection(points)

			// 	// Get the convex hull (the enclosing polygon)
			// 	const hull = turfConvex(featureCollection)

			// 	// Output the polygon coordinates (in GeoJSON format)
			// 	console.log(hull?.geometry.coordinates)
			// 	return hull?.geometry.coordinates
			// })
		},
	},
	actions: {
		/* You can define actions here and just call then like normal methods */
		setLoading() {
			this.loadingCount++
		},
		setLoadingDone() {
			this.loadingCount--
		},
		init() {
			this.setLoading()

			fetch('/events.json')
				.then((response) => {
					if (!response.ok) {
						throw new Error('Network response was not ok')
					}
					return response.json()
				})
				.then((data) => {
					this.endTime = new Date(0)
					this.events = data
					this.events.forEach((event) => {
						event.startTime = new Date(event.startTime)
						event.endTime = new Date(event.endTime)
						const startDate = new Date(event.startTime)
						if (startDate < this.startTime) {
							this.startTime = new Date(startDate)
						}
						startDate.setHours(0, 0, 0, 0)
						const endDate = new Date(event.endTime)
						if (endDate > this.endTime) {
							this.endTime = new Date(endDate)
						}
						endDate.setHours(23, 59, 59, 999)
						for (let d = startDate; d < endDate; d = addDays(d, 1)) {
							const dateStr = format(d, 'yyyy-MM-dd')
							if (!this.eventsByDay.has(dateStr)) {
								this.eventsByDay.set(dateStr, [])
							}
							this.eventsByDay.get(dateStr)?.push(event)
						}
					})
					this.setLoadingDone()
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
				})
		},
	},
})
