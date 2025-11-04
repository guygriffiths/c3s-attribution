import { finaliseEventFilters, manualGlobalTrigger } from '@/lib/eventFiltering'
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
	showAnalytics: boolean // Whether to show the analytics view in the ME panel

	hamburgerMenuOpen: boolean // Whether the side hamburger menu is open
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'
export const DATA_ROOT = `${import.meta.env.X_PUBLIC_PATH || ''}data/`

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			viewMode: 'timemachine', // 'timemachine' or 'heatmap'
			mapCentre: new LatLng(-20, 0) as unknown as Point, // Default center point for the map
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

			showMultiEventPanel: true,
			showAnalytics: false,

			hamburgerMenuOpen: false,
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

			let firstEventTime = new Date(9999, 0, 1)
			let lastEventTime = new Date(0)
			const massageData = (
				data: any[],
				type: 'hot' | 'cold' | 'wet' | 'windy' | 'dry',
			) => {
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

			const timeStore = useTimeStore()
			// TODO Unhard-code this
			const from = 1981
			const to = 2024
			timeStore.startTime = new Date(Date.UTC(from, 0, 1))
			timeStore.endTime = new Date(Date.UTC(to, 11, 31))

			const processYear = (year: number, objectsH: any, objectsC: any) => {
				console.log('processing year', year)
				const allEvents = [] as ExtremeEvent[]
				try {
					massageData(objectsH, 'hot')
					allEvents.push(...objectsH)
				} catch (e) {
					console.error('Error processing hot events:', e)
				}

				console.time(`Fetched cold events for year ${year}`)
				console.timeEnd(`Fetched cold events for year ${year}`)
				try {
					massageData(objectsC, 'cold')
					allEvents.push(...objectsC)
				} catch (e) {
					// console.error('Error processing cold events:', e)
				}
				console.time(`Processed events for year ${year}`)
				eventStore.addEvents(allEvents)
				console.timeEnd(`Processed events for year ${year}`)
			}

			const fetchData = async (year: number) => {
				const [hot, cold] = await Promise.all([
					fetch(`${DATA_ROOT}events-hot-${year}.jsonl`)
						.then((r) => r.text())
						// @ts-ignore
						.then((t) => t.trim().split('\n').map(JSON.parse))
						.catch((e) => {
							console.error('Error fetching hot', year, e)
							return []
						}),
						fetch(`${DATA_ROOT}events-cold-${year}.jsonl`)
						.then((r) => r.text())
						// @ts-ignore
						.then((t) => t.trim().split('\n').map(JSON.parse))
						.catch((e) => {
							console.error('Error fetching cold', year, e)
							return []
						}),
				])
				return { year, data: [hot, cold] }
			}
			// async function* fetchAndYield(years: number[]) {
			// 	const fetches = years.map(fetchData)

			// 	// yield as they complete
			// 	const pending = new Set(fetches)

			// 	while (pending.size) {
			// 		// Wait for the first one to finish
			// 		const res = await Promise.race(pending)
			// 		// Find the promise that resolved to res
			// 		for (const p of pending) {
			// 			p.then((val) => {
			// 				if (val === res) pending.delete(p)
			// 			})
			// 		}
			// 		yield res
			// 	}
			// }

			const latestData = await fetchData(to)
			processYear(to, latestData.data[0], latestData.data[1])
			manualGlobalTrigger()

			// Consumer with controlled processing
			const years = Array.from(
				{ length: to - from },
				(_, i) => from + i,
			).reverse()
			console.log('Starting fetch loop')
			for (const year of years) {
				const { data } = await fetchData(year)
				console.log(`Got data for year ${year}`, data)
				console.log('About to process year', year)
				processYear(year, data[0], data[1])
				console.log('Finished processing year', year)
				// @ts-ignore
				// await (scheduler?.yield?.() ?? new Promise((r) => setTimeout(r, 0)))
			}
			finaliseEventFilters()
			console.log('Finished all years')

			// console.time('Processed latest year first')
			// await processYear(to)()
			// console.timeEnd('Processed latest year first')
			// const promises = []
			// for (let year = to - 1; year >= from; year--) {
			// 	console.time(`setting up processing for year ${year}`)
			// 	const promise = processYear(year)
			// 	promises.push(promise())
			// 	console.timeEnd(`setting up processing for year ${year}`)
			// }
			// console.log('firing off all year processing')
			// await Promise.all(promises)
			// console.log('firing off all year processing done')
			manualGlobalTrigger()
		},
	},
})

export type MainStore = ReturnType<typeof useStore>
