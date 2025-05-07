import * as d3 from 'd3'
import { addDays, format, formatISO, parseISO } from 'date-fns'
import { defineStore } from 'pinia'

type LayerDetails = any

interface State {
	lang: Language
	loadingCount: number
	selectedTime: Date
	layerDetails: LayerDetails | null
	startTime: Date
	endTime: Date
	events: any[]
	eventsByDay: Map<string, any[]>
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'
export const catScheme = [...d3.schemePaired, ...d3.schemeSet3]

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			selectedTime: new Date(),
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
		// earliestDate: (state) => {
		// 	// return new Date(2022,0,1,0,0,0)
		// 	if (state.times.length > 0) {
		// 		return state.times[0]
		// 	}
		// },
		// latestDate: (state) => {
		// 	if (state.times.length > 0) {
		// 		return state.times[state.times.length - 1]
		// 	}
		// },
		isoDatetime: (state) => {
			return formatISO(state.selectedTime)
		},
		activeEvents: (state) => {
			const dateStr = format(state.selectedTime, 'yyyy-MM-dd')
			return state.eventsByDay.get(dateStr)
		}
	},
	actions: {
		/* You can define actions here and just call then like normal methods */
		setLoading() {
			this.loadingCount++
		},
		setLoadingDone() {
			this.loadingCount--
		},
		setDate(date: Date) {
			this.selectedTime = date
		},
		init() {
			this.setLoading()

			fetch(
				`${WMS_ROOT}?service=WMS&version=1.3.0&request=GetMetadata&item=layerDetails&layername=${T2M_LAYER}`,
			)
				.then((response) => {
					if (!response.ok) {
						throw new Error('Network response was not ok')
					}
					return response.json()
				})
				.then((data) => {
					this.layerDetails = data
					const datesWithData: Date[] = []
					Object.entries(this.layerDetails.datesWithData).forEach(
						(entry: [string, any]) => {
							const year: number = parseInt(entry[0])
							console.log('year', year, this.layerDetails)
							const months: any = entry[1]
							Object.entries(months).forEach((monthEntry: [string, any]) => {
								const month: number = parseInt(monthEntry[0])
								const days: any = monthEntry[1]
								days.forEach((day: number) => {
									// Don't need to subtract 1 from month, as the month is already 0-indexed
									datesWithData.push(new Date(year, month, day, 12, 0, 0))
								})
							})
						},
					)
					// TODO - this should probably contain every time in the range
					datesWithData.sort((a, b) => a.getTime() - b.getTime())
					this.startTime = datesWithData[0]
					this.endTime = datesWithData[datesWithData.length - 1]
					this.selectedTime = parseISO(this.layerDetails.nearestTimeIso)
					this.setLoadingDone()
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
					this.setLoadingDone()
				})

			fetch('/merged_clusters.json')
				.then((response) => {
					if (!response.ok) {
						throw new Error('Network response was not ok')
					}
					return response.json()
				})
				.then((data) => {
					this.events = data
					this.events.forEach((event) => {
						event.startTime = new Date(event.startTime)
						event.endTime = new Date(event.endTime)
						const startDate = new Date(event.startTime)
						startDate.setHours(0, 0, 0, 0)
						const endDate = new Date(event.endTime)
						endDate.setHours(23, 59, 59, 999)
						for (let d = startDate; d < endDate; d = addDays(d, 1)) {
							const dateStr = format(d, 'yyyy-MM-dd')
							if(!this.eventsByDay.has(dateStr)) {
								this.eventsByDay.set(dateStr, [])
							}
							this.eventsByDay.get(dateStr)?.push(event)
						}
					})
					console.log('events', this.eventsByDay)
				})
				.catch((error) => {
					console.error('There was a problem with the fetch operation:', error)
				})
		},
	},
})
