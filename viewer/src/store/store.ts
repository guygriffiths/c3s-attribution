import * as d3 from 'd3'
import { addHours, differenceInDays } from 'date-fns'
import { LatLng, Point } from 'leaflet'
import { defineStore } from 'pinia'
import { watch } from 'vue'
import { useStore as useEventStore } from './eventStore'
import { useStore as useTimeStore } from './timeStore'

type LayerDetails = any

interface State {
	lang: Language
	loadingCount: number
	viewMode: ViewMode
	mapCentre: Point
	// This holds a reference to a window through a panel through which the map is viewed
	// So we want to fit to these bounds, centre our zoom events here, etc.
	mapPeephole: HTMLElement | null

	layerDetails: LayerDetails | null

	lat2Index?: (lat: number) => number
	lon2Index?: (lon: number) => number

	filtersExpanded: boolean
	filters: {
		duration: number
		intensity: number
		size: number
		includeOceanEvents: boolean
	}
	lastPoint: [number, number] | null // This is used to store the last point selected on the map for filtering
	filteringByRegion: boolean // Whether we are currently drawing a region on the map
	filteringByPoint: boolean // Whether we are currently filtering by a point
	regionFilterReady: boolean // Whether we are currently drawing a region on the map

	draggingFilter: boolean

	showMultiEventPanel: boolean // Whether to show the multi-event summary panel
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			viewMode: 'timemachine', // 'timemachine' or 'heatmap'
			mapCentre: new LatLng(0, 0) as unknown as Point, // Default center point for the map
			mapPeephole: null, // This will be set to the map container element when the map is initialized

			layerDetails: null,

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
			filtersExpanded: false,
			filters: {
				duration: 3,
				intensity: 0,
				size: 0,
				includeOceanEvents: true, // Whether to include ocean events in the filter
			},
			draggingFilter: false,
			lastPoint: null,
			filteringByRegion: false,
			regionFilterReady: false, // Whether we are currently drawing a region on the map
			filteringByPoint: false, // Whether we are currently filtering by a point

			showMultiEventPanel: false,
		}
	},
	getters: {
		exploreGlobal: (state) => {
			return !state.filteringByPoint && !state.regionFilterReady
		},
		isFocused: (state) => {
			const eventStore = useEventStore()
			return eventStore.selectedEventId !== null
		},
		exploringRegion: (state) => {
			return state.regionFilterReady || state.filteringByPoint
		},
		isLoading: (state) => state.loadingCount > 0,
		// Returns the (filtered) events which are active at the selected time (i.e. plotted on the map)
		// TODO make it respond to a range, and use this is region explore
	},
	actions: {
		async setLoading() {
			this.loadingCount++
			// Triggers Vue to re-render the map
			await new Promise((resolve) => setTimeout(resolve, 0))
		},
		setLoadingDone() {
			this.loadingCount--
		},

		async init() {
			this.setLoading()
			const eventStore = useEventStore()
			watch(() => [this.filters], eventStore.runFilters, {
				deep: true,
				immediate: false,
			})
			watch(
				() => this.viewMode,
				() => {
					if (this.viewMode === 'timemachine') {
					}
				},
			)

			const respH = await fetch('/events-hw.jsonl')
			if (!respH.ok) {
				throw new Error('Network response was not ok')
			}
			const textH = await respH.text()
			const linesH = textH.trim().split('\n')
			const objectsH = linesH.map((line) => JSON.parse(line))
			const data = objectsH

			let firstEventTime = new Date(9999, 0, 1)
			let lastEventTime = new Date(0)
			const massageData = (data: any[], type: 'hot' | 'cold' | 'wet' | 'windy' | 'dry') => {
				data.forEach((event: any) => {
					// console.log('Processing event:', event)
					event.times = event.times.map((time: string) => new Date(time))
					const startDate = new Date(event.times[0])
					if (startDate < firstEventTime) {
						firstEventTime = new Date(startDate)
					}
					startDate.setHours(0, 0, 0, 0)
					const endDate = addHours(
						new Date(event.times[event.times.length - 1]),
						24,
					)
					if (endDate > lastEventTime) {
						lastEventTime = new Date(endDate)
					}

					event.duration =
						1 +
						differenceInDays(
							event.times[event.times.length - 1],
							event.times[0],
						)
					event.event_type = type
				})
			}
			massageData(data, 'hot')

			const respC = await fetch('/events-cw.jsonl')
			if (!respC.ok) {
				throw new Error('Network response was not ok')
			}
			const textC = await respC.text()
			const linesC = textC.trim().split('\n')
			const objectsC = linesC.map((line) => JSON.parse(line))
			massageData(objectsC, 'cold')
			data.push(...objectsC)

			const timeStore = useTimeStore()
			timeStore.startTime = new Date(
				Date.UTC(firstEventTime.getUTCFullYear(), 0, 1),
			)
			timeStore.endTime = new Date(
				Date.UTC(lastEventTime.getUTCFullYear(), 11, 31),
			)
			eventStore.setEvents(data as ExtremeEvent[])
			this.setLoadingDone()

		},
	},
})

export type MainStore = ReturnType<typeof useStore>
