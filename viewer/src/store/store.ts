import * as d3 from 'd3'
import { LatLng, Point } from 'leaflet'
import { defineStore } from 'pinia'
import { useStore as useEventStore } from './eventStore'

type LayerDetails = any

interface State {
	lang: Language
	// Loading count + message for main blocking indicator
	loadingCount: number
	loadingMessage: string | null
	// Soft loading counts for non-blocking indicators
	mapSoftLoadingCount: number
	eventSoftLoadingCount: number

	viewMode: ViewMode
	mapCentre: Point

	lat2Index?: (lat: number) => number
	lon2Index?: (lon: number) => number

	lastPoint: [number, number] | null // This is used to store the last point selected on the map for filtering
	filteringByRegion: boolean // Whether we are currently drawing a region on the map
	regionFilterReady: boolean // Whether we are currently drawing a region on the map

	filteringByPoint: boolean // Whether we are currently filtering by a point
	draggingFilter: boolean

	showMultiEventPanel: boolean // Whether to show the multi-event summary panel
	showAnalytics: boolean // Whether to show the analytics view in the ME panel

	hamburgerMenuOpen: boolean // Whether the side hamburger menu is open
}

export const WMS_ROOT = 'http://localhost:8080/ncWMS2/wms'
export const T2M_LAYER = 'era5/t2m'

export const useStore = defineStore('main', {
	state: (): State => {
		return {
			lang: 'en',
			loadingCount: 0,
			loadingMessage: null,
			mapSoftLoadingCount: 0,
			eventSoftLoadingCount: 0,
			viewMode: 'timemachine', // 'timemachine' or 'heatmap'
			mapCentre: new LatLng(-20, 0) as unknown as Point, // Default center point for the map

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
	},
	actions: {
		async setLoading(message: string | null = null) {
			this.loadingCount++
			this.loadingMessage = message
			console.log('Set loading, count =', this.loadingCount, 'message=', message)
			if (this.loadingCount === 1) {
				const loadingOverlay = document.getElementById('loading-overlay')
				if (loadingOverlay) {
					loadingOverlay.style.display = 'flex'

					// FORCE immediate paint before returning
					void loadingOverlay.offsetHeight // Trigger reflow
				}
			}
			await new Promise((resolve) => requestAnimationFrame(resolve))
			await new Promise((resolve) => requestAnimationFrame(resolve))
		},
		async setLoadingDone() {
			this.loadingCount--
			console.log('Set loading done, count =', this.loadingCount)
			if (this.loadingCount === 0) {
				const loadingOverlay = document.getElementById('loading-overlay')
				if (loadingOverlay) loadingOverlay.style.display = 'none'
				this.loadingMessage = null
			}
		},
		setEventLoading() {
			this.eventSoftLoadingCount++
		},
		setEventLoadingDone() {
			this.eventSoftLoadingCount--
		},
	}
})

export type MainStore = ReturnType<typeof useStore>
