import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	buildEventFilters,
	manualGlobalTrigger,
	setPostFilters
} from '@/lib/eventFiltering'
import { interpolateColorCold, interpolateColorHot } from '@/lib/utils'
import * as d3 from 'd3'
import { differenceInDays } from 'date-fns'
import { defineStore } from 'pinia'
import { DATA_ROOT, useStore as useMainStore } from './store'
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

	eventTypeMode: 'hot' | 'cold' | 'hotcold'
	sizeRange: [number, number]

	eventSetsLoaded: number
}

export const intensityForValue = (v: number, hot: boolean) => {
	if (v == null || isNaN(v)) return 0
	if (hot) {
		let baseline = 301.15
		return v - baseline
	} else {
		let baseline = 275.15
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
		return interpolateColorHot(scssVars.c3sred)(scale(v))
	} else {
		return interpolateColorCold(scssVars.c3sblue)(scale(v))
	}
}

export const colorForEvent = (
	event: ExtremeEvent,
	scale: d3.ScaleLinear<number, number>,
) => {
	const value = intensityForValue(
		event.event_type === 'hot' ? event.max_value : event.mean_value,
		event.event_type === 'hot',
	)
	console.log('intensity for event', event.id, 'is', value, intensityForValue, colorForValue)
	return colorForValue(value, event.event_type === 'hot', scale)
}

export const useStore = defineStore('events', {
	state: (): State => {
		return {
			selectedEvent: null,
			selectedEventId: null,
			startYear: 2024,
			endYear: 2024,
			hoveringEventId: null,
			durationRange: [3, 14],
			heatIntensityRange: [0, 0],
			coldIntensityRange: [0, 0],
			eventTypeMode: 'hot',
			sizeRange: [0, 100],
			eventSetsLoaded: 0,
		}
	},
	getters: {
		intensityRange: (state: State) => {
			if (state.eventTypeMode === 'hotcold') {
				return [
					Math.min(state.coldIntensityRange[0], state.heatIntensityRange[0]),
					Math.max(state.coldIntensityRange[1], state.heatIntensityRange[1]),
				]
			} else if (state.eventTypeMode === 'hot') {
				return state.heatIntensityRange
			} else if (state.eventTypeMode === 'cold') {
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
			return (event: ExtremeEvent | ExtremeEventFull) => {
				const hot = event.event_type === 'hot'
				return colorForValue(
					// @ts-ignore - this is a getter
					state.intensityForEvent(event),
					hot,
					// @ts-ignore - these are getters
					hot ? state.hotScale : state.coldScale,
				)
			}
		},
		durationForEvent: (state: State) => {
			return (event: ExtremeEvent | ExtremeEventFull | null) =>
				event?.duration || 0
		},
		sizeForEvent: (state: State) => {
			return (event: ExtremeEvent | ExtremeEventFull | null) =>
				event?.total_area || 0
		},
		intensityForEvent: (state: State) => {
			return (event: ExtremeEvent | ExtremeEventFull | null) => {
				if (!event) return 0
				return intensityForValue(
					event.event_type === 'hot' ? event.max_value : event.mean_value,
					event.event_type === 'hot',
				)
			}
		},
		sizesForEvent: (state: State) => {
			return (event: ExtremeEventFull | null) => {
				if (!event) return []
				return event.areas
			}
		},
		intensitiesForEvent: (state: State) => {
			return (event: ExtremeEventFull | null) => {
				if (!event) return []
				if (event.event_type === 'hot') {
					return event.max_values.map((v) => intensityForValue(v, true))
				} else {
					return event.mean_values.map((v) => intensityForValue(v, false))
				}
			}
		},
		intensitiesForEventStep: (state: State) => {
			return (event: ExtremeEventFull | null, time: Date) => {
				if (!event) return []
				const idx = event.times.findIndex((t) => t.getTime() === time.getTime())
				if (idx === -1) return []
				if (event.event_type === 'hot') {
					return event.values[idx].map((v) => intensityForValue(v, true))
				} else {
					return event.values[idx].map((v) => intensityForValue(v, false))
				}
			}
		},
		downloadLinkForEvent: (state: State) => {
			return (event: ExtremeEventFull | null) => {
				if (!event) return ''
				const dataStr =
					'data:text/json;charset=utf-8,' +
					encodeURIComponent(JSON.stringify(event))
				return dataStr
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
				let path = `${DATA_ROOT}events/event-${id}.json`
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
		async addEvents(data: ExtremeEvent[], final: boolean = false) {
			const mainStore = useMainStore()
			// console.log(
			// 	'Setting events, count:',
			// 	data.length,
			// 	data.filter((e) => e.event_type === 'hot').length,
			// 	data.filter((e) => e.event_type === 'cold').length,
			// )
			// Throw away the top x% of values for setting the range on colour scales, histograms etc
			// const N = Math.ceil(data.length * 0.025)

			// Preprocess events a bit
			const durations = data
				.map((e) => this.durationForEvent(e))
				.filter((v) => v != null)
				.sort((a, b) => b - a)

			const heatIntensities = data
				.filter((d) => d != null && d.event_type === 'hot')
				.map((e) => this.intensityForEvent(e))
				.sort((a, b) => b - a)
			// console.log('heat intensities', heatIntensities)

			const coldIntensities = data
				.filter((d) => d != null && d.event_type === 'cold')
				.map((e) => this.intensityForEvent(e))
				.sort((a, b) => b - a)
			// console.log('cold intensities', coldIntensities)

			const sizes = data
				.map((e) => this.sizeForEvent(e))
				.filter((v) => v != null)
				.sort((a, b) => b - a)

			if (durations.length > 0) {
				this.durationRange = [
					Math.min(durations[durations.length - 1], this.durationRange[0]),
					Math.max(durations[0], this.durationRange[1]),
				]
			}
			if (heatIntensities.length > 0) {
				this.heatIntensityRange = [
					Math.min(
						heatIntensities[heatIntensities.length - 1],
						this.heatIntensityRange[0],
					),
					Math.max(heatIntensities[0], this.heatIntensityRange[1]),
				]
			}
			if (coldIntensities.length > 0) {
				this.coldIntensityRange = [
					Math.min(
						coldIntensities[coldIntensities.length - 1],
						this.coldIntensityRange[0],
					),
					Math.max(coldIntensities[0], this.coldIntensityRange[1]),
				]
			}

			this.sizeRange = [0, Math.max(sizes[sizes.length - 1], this.sizeRange[1])]

			// console.time('ES:buildEventFilters')
			buildEventFilters(data) // Kick off building the pixel index
			// console.timeEnd('ES:buildEventFilters')
			this.eventSetsLoaded += 1
			if(this.eventSetsLoaded === 1) {
				mainStore.setLoadingDone()
			}
			if (
				this.eventSetsLoaded <= 3 ||
				this.eventSetsLoaded === 5 ||
				this.eventSetsLoaded % 10 === 0 || final
			) {
				console.log('Manually triggering global events ready callback after', this.eventSetsLoaded, 'sets loaded')
				// Trigger a global events ready callback at various points during loading
				// This allows a good balance between early rendering and processing speed
				// (rendering after every year is slow, particularly compared with data loads from cache)
				manualGlobalTrigger()
			}

			this.startYear = Math.min(
				data[0].times[0].getUTCFullYear(),
				this.startYear,
			)
			this.endYear = Math.max(
				data[0].times[data[0].times.length - 1].getUTCFullYear(),
			)
		},
	},
})

export type MainStore = ReturnType<typeof useStore>
