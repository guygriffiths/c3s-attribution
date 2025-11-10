import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	fetchAndIndexEvents,
	getGlobalFilteredEvents,
	onGlobalEventsReady,
	setPostFilters,
} from '@/lib/eventsDB'
import {
	DATA_ROOT,
	interpolateColorCold,
	interpolateColorHot,
} from '@/lib/utils'
import * as d3 from 'd3'
import { defineStore } from 'pinia'
import { watch } from 'vue'
import { useStore as useMainStore } from './store'
import { useStore as useTimeStore } from './timeStore'

interface State {
	selectedEvent: ExtremeEventFull | null
	selectedEventId: string | null
	hoveringEventId: string | null

	durationRange: [number, number]
	heatIntensityRange: [number, number]
	coldIntensityRange: [number, number]
	sizeRange: [number, number]

	eventTypeMode: 'hot' | 'cold' | 'hotcold'

	eventSetsLoaded: number

	filters: {
		duration: number
		intensity: number
		size: number
	}
	firstEventSetLoaded: boolean
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
	console.log(
		'intensity for event',
		event.id,
		'is',
		value,
		intensityForValue,
		colorForValue,
	)
	return colorForValue(value, event.event_type === 'hot', scale)
}

export const useStore = defineStore('events', {
	state: (): State => {
		return {
			selectedEvent: null,
			selectedEventId: null,
			hoveringEventId: null,
			durationRange: [3, 14],
			heatIntensityRange: [0, 0],
			coldIntensityRange: [0, 0],
			eventTypeMode: 'hot',
			sizeRange: [0, 100],
			eventSetsLoaded: 0,
			filters: {
				duration: 3,
				intensity: 0,
				size: 0,
			},
			firstEventSetLoaded: false,
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
				event?.times.length || 0
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
				const idx = event.times.findIndex((t) => t === time.getTime())
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
				// mainStore.setLoading()
				this.selectedEventId = id
				console.log('setting selected event to', id)
				let path = `${DATA_ROOT}events/event-${id}.json`
				const resp = await fetch(path)
				const event = await resp.json()
				// // This should always be the case...
				event.id = id
				event.times = event.times.map((time: string) =>
					new Date(time).getTime(),
				)
				this.selectedEvent = event as ExtremeEventFull
				if (
					timeStore.selectedTime < event.times[0] ||
					timeStore.selectedTime > event.times[event.times.length - 1]
				) {
					timeStore.selectedTime = new Date(event.times[0])
				}
				// mainStore.setLoadingDone()
			}
		},
		async runFilters() {
			console.log('Running event filters')
			const mainStore = useMainStore()
			mainStore.setLoading()

			setPostFilters(
				this.filters,
				this.durationForEvent,
				this.intensityForEvent,
				this.sizeForEvent,
			)
			// This needs to get set by the leaflet layers
			mainStore.setLoadingDone()
		},
		// async addEvents(data: ExtremeEvent[], final: boolean = false) {
		// 	const mainStore = useMainStore()
		// 	// console.log(
		// 	// 	'Setting events, count:',
		// 	// 	data.length,
		// 	// 	data.filter((e) => e.event_type === 'hot').length,
		// 	// 	data.filter((e) => e.event_type === 'cold').length,
		// 	// )
		// 	// Throw away the top x% of values for setting the range on colour scales, histograms etc
		// 	// const N = Math.ceil(data.length * 0.025)

		// 	data.forEach((e) => {
		// 		const duration = this.durationForEvent(e)
		// 		if (duration < this.durationRange[0]) {
		// 			this.durationRange[0] = duration
		// 		}
		// 		if (duration > this.durationRange[1]) {
		// 			this.durationRange[1] = duration
		// 		}

		// 		const size = this.sizeForEvent(e)
		// 		if (size < this.sizeRange[0]) {
		// 			this.sizeRange[0] = size
		// 		}
		// 		if (size > this.sizeRange[1]) {
		// 			this.sizeRange[1] = size
		// 		}

		// 		const intensity = intensityForValue(
		// 			e.event_type === 'hot' ? e.max_value : e.mean_value,
		// 			e.event_type === 'hot',
		// 		)
		// 		if (e.event_type === 'hot') {
		// 			if (intensity < this.heatIntensityRange[0]) {
		// 				this.heatIntensityRange[0] = intensity
		// 			}
		// 			if (intensity > this.heatIntensityRange[1]) {
		// 				this.heatIntensityRange[1] = intensity
		// 			}
		// 		} else if (e.event_type === 'cold') {
		// 			if (intensity < this.coldIntensityRange[0]) {
		// 				this.coldIntensityRange[0] = intensity
		// 			}
		// 			if (intensity > this.coldIntensityRange[1]) {
		// 				this.coldIntensityRange[1] = intensity
		// 			}
		// 		}
		// 	})

		// 	console.time('ES:buildEventFilters')
		// 	buildEventFilters(data) // Kick off building the pixel index
		// 	console.timeEnd('ES:buildEventFilters')
		// 	this.eventSetsLoaded += 1
		// 	if (this.eventSetsLoaded === 1) {
		// 		mainStore.setLoadingDone()
		// 	}
		// 	if (
		// 		this.eventSetsLoaded <= 3 ||
		// 		this.eventSetsLoaded === 5 ||
		// 		this.eventSetsLoaded % 10 === 0 ||
		// 		final
		// 	) {
		// 		// console.log('Manually triggering global events ready callback after', this.eventSetsLoaded, 'sets loaded')
		// 		// Trigger a global events ready callback at various points during loading
		// 		// This allows a good balance between early rendering and processing speed
		// 		// (rendering after every year is slow, particularly compared with data loads from cache)
		// 		manualGlobalTrigger()
		// 	}
		// },
		async init() {
			this.firstEventSetLoaded = false
			const mainStore = useMainStore()
			mainStore.setLoading()
			watch(() => [this.filters], this.runFilters, {
				deep: true,
				immediate: false,
			})

			// Hard-code start date, get end date from current year.
			const timeStore = useTimeStore()
			const from = 1979
			const to = 2024 //new Date().getFullYear()
			timeStore.startTime = new Date(Date.UTC(from, 0, 1))
			timeStore.endTime = new Date(Date.UTC(to, 11, 31))

			onGlobalEventsReady(() => {
				const events = getGlobalFilteredEvents()
				if (events.length > 0) {
					if (!this.firstEventSetLoaded) {
						this.firstEventSetLoaded = true
						console.log('First event set loaded, clearing loading state')
						mainStore.setLoadingDone()
					} else {
						console.log('Setting loading...')
						// mainStore.setLoading()
					}
				}
				events.forEach((e) => {
					const duration = this.durationForEvent(e)
					if (duration < this.durationRange[0]) {
						this.durationRange[0] = duration
					}
					if (duration > this.durationRange[1]) {
						this.durationRange[1] = duration
					}

					const size = this.sizeForEvent(e)
					if (size < this.sizeRange[0]) {
						this.sizeRange[0] = size
					}
					if (size > this.sizeRange[1]) {
						this.sizeRange[1] = size
					}

					const intensity = intensityForValue(
						e.event_type === 'hot' ? e.max_value : e.mean_value,
						e.event_type === 'hot',
					)
					if (e.event_type === 'hot') {
						if (intensity < this.heatIntensityRange[0]) {
							this.heatIntensityRange[0] = intensity
						}
						if (intensity > this.heatIntensityRange[1]) {
							this.heatIntensityRange[1] = intensity
						}
					} else if (e.event_type === 'cold') {
						if (intensity < this.coldIntensityRange[0]) {
							this.coldIntensityRange[0] = intensity
						}
						if (intensity > this.coldIntensityRange[1]) {
							this.coldIntensityRange[1] = intensity
						}
					}
				})
			})

			// Load hot and cold events
			await fetchAndIndexEvents(['hot', 'cold'], from, to)
		},
	},
})

export type EventStore = ReturnType<typeof useStore>
