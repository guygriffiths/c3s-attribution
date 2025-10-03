import scssVars from '@/assets/styles/scssVars.module.scss'
import { buildEventFilters, setPostFilters } from '@/lib/eventFiltering'
import { interpolateColor } from '@/lib/utils'
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

	durationRange: [number, number]
	heatIntensityRange: [number, number]
	coldIntensityRange: [number, number]
	hotEventsOn: boolean
	coldEventsOn: boolean
	sizeRange: [number, number]
}

export const intensityForValue = (v: number, hot: boolean) => {
	if (hot) {
		let baseline = 278.15
		return v - baseline
	} else {
		let baseline = 271.15
		return baseline - v
	}
}

export const colorForValue = (
	v: number,
	hot: boolean,
	scale: d3.ScaleLinear<number, number>,
) => {
	// if (!event || !scale) return (v: number) => 'transparent'
	if (hot) {
		return interpolateColor(scssVars.c3sred)(scale(v))
	} else {
		return interpolateColor(scssVars.c3sblue)(scale(v))
	}
}

export const colorForEvent = (
	event: ExtremeEvent,
	scale: d3.ScaleLinear<number, number>,
) => {
	
	const value = intensityForValue(event.peak_value, event.event_type === 'hot')
	return colorForValue(value, event.event_type === 'hot', scale)
}

export const useStore = defineStore('events', {
	state: (): State => {
		return {
			selectedEvent: null,
			selectedEventId: null,
			startYear: 1979,
			endYear: new Date().getUTCFullYear(),
			hoveringEventId: null,
			durationRange: [3, 14],
			heatIntensityRange: [305, 320],
			coldIntensityRange: [270, 250],
			hotEventsOn: false,
			coldEventsOn: true,
			sizeRange: [0, 100],
		}
	},
	getters: {
		dualMode: (state: State) => {
			return state.hotEventsOn && state.coldEventsOn
		},
		intensityRange: (state: State) => {
			if (state.hotEventsOn && state.coldEventsOn) {
				return [
					Math.min(state.coldIntensityRange[0], state.heatIntensityRange[0]),
					Math.max(state.coldIntensityRange[1], state.heatIntensityRange[1]),
				]
			} else if (state.hotEventsOn) {
				return state.heatIntensityRange
			} else if (state.coldEventsOn) {
				return state.coldIntensityRange
			} else {
				return [0, 1]
			}
		},
		eventSelected: (state: State) => {
			return state.selectedEventId !== null // && state.selectedEvent !== undefined
		},
		hotScale: (state: State) => {
			return d3
				.scaleLinear()
				.domain(state.heatIntensityRange)
				.range([0, 1])
				.clamp(true)
		},
		coldScale: (state: State) => {
			return d3
				.scaleLinear()
				.domain(state.coldIntensityRange)
				.range([0, 1])
				.clamp(true)
		},
		colorForEvent: (state: State) => {
			// TODO Logic for configurable intensity definition.
			return (event: ExtremeEvent) => {
				const hot = event.event_type === 'hot'
				return colorForValue(
					state.intensityForEvent(event),
					hot,
					hot ? state.hotScale : state.coldScale,
				)
			}
		},
		durationForEvent: (state: State) => {
			return (event: ExtremeEvent) => event.duration
		},
		sizeForEvent: (state: State) => {
			return (event: ExtremeEvent) => event.pixel_set?.length || 0
		},
		intensityForEvent: (state: State) => {
			return (event: ExtremeEvent) => {
				return intensityForValue(event.peak_value, event.event_type === 'hot')
			}
		},
	},
	actions: {
		async selectEvent(id: string | null) {
			const mainStore = useMainStore()
			const timeStore = useTimeStore()
			if (id === null) {
				this.selectedEvent = null
				this.selectedEventId = null
				return
			}
			// if (this.selectedEvent?.id === id) {
			if (this.selectedEventId === id) {
				this.selectedEvent = null
				this.selectedEventId = null
			} else {
				mainStore.setLoading()
				this.selectedEventId = id
				console.log('setting selected event to', id)
				let path = `/events/event-${id}.json`
				const resp = await fetch(path)
				const event = await resp.json()
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
				event.max_value = event.peak_value
				event.min_value = event.mean_value - (event.peak_value - event.mean_value)
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

			setPostFilters(
				mainStore.filters,
				this.durationForEvent,
				this.intensityForEvent,
				this.sizeForEvent,
			)
			// This needs to get set by the leaflet layers
			mainStore.setLoadingDone()
		},
		setEvents(data: ExtremeEvent[]) {
			console.log(
				'Setting events, count:',
				data.length,
				data.filter((e) => e.event_type === 'hot').length,
				data.filter((e) => e.event_type === 'cold').length,
			)
			const mainStore = useMainStore()
			// Throw away the top x% of values for setting the range on colour scales, histograms etc
			const N = Math.ceil(data.length * 0.025)
			mainStore.setLoading()
			// Preprocess events a bit
			const durations = data
				.map((e) => this.durationForEvent(e))
				.filter((v) => v != null)
				.sort((a, b) => b - a)

			const heatIntensities = data
				.filter((d) => d != null && d.event_type === 'hot')
				.map((e) => this.intensityForEvent(e))
				.sort((a, b) => b - a)

			const coldIntensities = data
				.filter((d) => d != null && d.event_type === 'cold')
				.map((e) => this.intensityForEvent(e))
				.sort((a, b) => b - a)

			const sizes = data
				.map((e) => this.sizeForEvent(e))
				.filter((v) => v != null)
				.sort((a, b) => b - a)

			this.durationRange = [
				Math.max(3, durations[durations.length - 1]),
				durations[Math.min(Math.floor(0.1 * N), durations.length - 1)],
			]
			this.heatIntensityRange = [
				heatIntensities[heatIntensities.length - 1],
				heatIntensities[
					Math.min(Math.floor(0.1 * N), heatIntensities.length - 1)
				],
			]
			console.log('heat intensity range', this.heatIntensityRange)
			// This is if we want to reverse the cold scale so that "more extreme" is always lower
			// this.coldIntensityRange = [
			// 	coldIntensities[Math.min(N, coldIntensities.length - 1)],
			// 	coldIntensities[coldIntensities.length - 1],
			// ]
			this.coldIntensityRange = [
				coldIntensities[coldIntensities.length - 1],
				coldIntensities[
					Math.min(Math.floor(0.1 * N), coldIntensities.length - 1)
				],
			]
			console.log('cold intensity range', this.coldIntensityRange)

			this.sizeRange = [
				sizes[sizes.length - 1],
				sizes[Math.min(N, sizes.length - 1)],
			]

			buildEventFilters(data) // Kick off building the pixel index

			this.startYear = data[0].times[0].getUTCFullYear()
			this.endYear = data[0].times[data[0].times.length - 1].getUTCFullYear()

			mainStore.setLoadingDone()
		},
	},
})

export type MainStore = ReturnType<typeof useStore>
