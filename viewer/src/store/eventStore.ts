import { buildEventFilters, setPostFilters } from '@/lib/eventFiltering'
import * as d3 from 'd3'
import { differenceInDays } from 'date-fns'
import { defineStore } from 'pinia'
import { useStore as useMainStore } from './store'
import { useStore as useTimeStore } from './timeStore'

// const worker = createEventFilterWorker()
// let spatialIndex: Flatbush | null = null // Spatial index for events

interface State {
	// events: ExtremeEvent[]
	startYear: number
	endYear: number

	selectedEvent: ExtremeEventFull | null
	selectedEventId: string | null
	hoveringEventId: string | null

	// These are the events after having the threshold filters applied
	// globalFilteredEvents: ExtremeEvent[]

	minDuration: number
	maxDuration: number
	minIntensity: number
	maxIntensity: number
	minSize: number
	maxSize: number
}

export const useStore = defineStore('events', {
	state: (): State => {
		return {
			selectedEvent: null,
			selectedEventId: null,
			startYear: 1979,
			endYear: new Date().getUTCFullYear(),
			hoveringEventId: null,
			minDuration: 3,
			maxDuration: 14,
			minIntensity: 300,
			maxIntensity: 330,
			minSize: 0,
			maxSize: 100,
		}
	},
	getters: {
		eventSelected: (state: State) => {
			return state.selectedEventId !== null // && state.selectedEvent !== undefined
		},
		colorForEvent: (state: State) => {
			const scale = d3
				.scaleLinear()
				// @ts-ignore
				.domain(state.intensityRange)
				.range([0, 1])
				.clamp(true)
			// TODO Logic for configurable intensity definition.
			return (event: ExtremeEvent) => {
				return d3.interpolateWarm(scale(event.peak_value || 0))
			}
		},
		durationForEvent: (state: State) => {
			return (event: ExtremeEvent) => event.duration
		},
		durationRange: (state: State): [number, number] => {
			return [state.minDuration, state.maxDuration]
		},
		intensityForEvent: (state: State) => {
			// TODO This should be configurable between min/max/mean, something else?
			return (event: ExtremeEvent) => event.peak_value
		},
		intensityRange: (state: State): [number, number] => {
			// TODO - Definition of intensity should be configurable
			return [state.minIntensity, state.maxIntensity]
		},
		sizeForEvent: (state: State) => {
			return (event: ExtremeEvent) => event.pixel_set?.length || 0
		},
		sizeRange: (state: State): [number, number] => {
			// TODO - Definition of size should be configurable
			return [state.minSize, state.maxSize]
		},
	},
	actions: {
		async selectEvent(id: string | null) {
			console.log('Clicked select', id)
			const mainStore = useMainStore()
			const timeStore = useTimeStore()
			if (id === null) {
				this.selectedEvent = null
				this.selectedEventId = null
				return
			}
			// if (this.selectedEvent?.id === id) {
			if (this.selectedEventId === id) {
				console.log('Deselecting event', id)
				this.selectedEvent = null
				this.selectedEventId = null
			} else {
				mainStore.setLoading()
				this.selectedEventId = id
				let path = `/events/event-${id}.json`
				const resp = await fetch(path)
				const event = await resp.json()
				console.log('Fetched event details', event)
				// // This should always be the case...
				event.id = id
				event.times = event.times.map((time: string) => new Date(time))
				event.duration =
					1 +
					differenceInDays(event.times[event.times.length - 1], event.times[0])
				this.selectedEvent = event as ExtremeEventFull
				if (
					timeStore.selectedTime < event.times[0] ||
					timeStore.selectedTime > event.times[event.times.length - 1]
				) {
					timeStore.selectedTime = new Date(event.times[0])
				}
				mainStore.setLoadingDone()
			}
		},
		toggleEventSelectedDebug() {
			this.selectedEvent =
				this.selectedEvent === null ? (new Object() as ExtremeEventFull) : null
		},
		async runFilters() {
			console.log('Running event filters')
			const mainStore = useMainStore()
			mainStore.setLoading()

			setPostFilters(mainStore.filters)
			// This needs to get set by the leaflet layers
			mainStore.setLoadingDone()
		},
		setEvents(data: ExtremeEvent[]) {
			console.log('Setting events, count:', data.length)
			const mainStore = useMainStore()
			mainStore.setLoading()
			// Preprocess events a bit
			let minDuration = Infinity,
				maxDuration = -Infinity
			let minIntensity = Infinity,
				maxIntensity = -Infinity
			let minSize = Infinity,
				maxSize = -Infinity
			for (const e of data) {
				if (this.durationForEvent(e) != null) {
					minDuration = Math.min(minDuration, this.durationForEvent(e))
					maxDuration = Math.max(maxDuration, this.durationForEvent(e))
				}
				if (this.intensityForEvent(e) != null) {
					minIntensity = Math.min(minIntensity, this.intensityForEvent(e))
					maxIntensity = Math.max(maxIntensity, this.intensityForEvent(e))
				}
				if (this.sizeForEvent(e) != null) {
					minSize = Math.min(minSize, this.sizeForEvent(e))
					maxSize = Math.max(maxSize, this.sizeForEvent(e))
				}
			}
			this.minDuration = minDuration
			this.maxDuration = maxDuration
			this.minIntensity = minIntensity
			this.maxIntensity = maxIntensity
			this.minSize = minSize
			this.maxSize = maxSize
			console.log('Compute event stats', minSize, maxSize)

			// this.events = data
			// console.log('Stored events')

			buildEventFilters(data) // Kick off building the pixel index

			this.startYear = data[0].times[0].getUTCFullYear()
			this.endYear = data[0].times[data[0].times.length - 1].getUTCFullYear()

			mainStore.setLoadingDone()
		},
	},
})

export type MainStore = ReturnType<typeof useStore>
