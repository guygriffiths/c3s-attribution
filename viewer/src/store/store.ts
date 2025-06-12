import * as d3 from 'd3'
import { differenceInDays } from 'date-fns'
import { defineStore } from 'pinia'

type LayerDetails = any

interface Event {
	times: number[]
	startTime: Date
	endTime: Date
	slices: any[]
	regions: any[]
	maxArea: number
	bbox: [number, number, number, number]
	centroid: [number, number]
	size: number
	feature: boolean
}

interface State {
	lang: Language
	loadingCount: number
	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: Event[]
	selectedEvent?: Event | null
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
			selectedEvent: null,
		}
	},
	getters: {
		isLoading: (state) => state.loadingCount > 0,
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
		selectedTimeIndex: (state) => {
			// Find the index of the selected time in the times array
			return differenceInDays(
				state.selectedTime,
				state.startTime,
			)
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
					})
					this.setLoadingDone()
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
				})
		},
	},
})
