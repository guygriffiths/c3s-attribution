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
	hoveringEvent: ExtremeEvent | null

	durationRange: [number, number]
	durationUnits: string
	sizeRange: [number, number]
	sizeUnits: string
	heatIntensityRange: [number, number]
	heatIntensityUnits: string
	coldIntensityRange: [number, number]
	coldIntensityUnits: string
	durationP90: number | null
	sizeP90: number | null
	heatIntensityP90: number | null
	coldIntensityP90: number | null

	eventTypeMode: 'hot' | 'cold' | 'hotcold'

	eventSetsLoaded: number

	filters: Filters
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
			hoveringEvent: null,
			durationRange: [3, 14],
			durationUnits: 'days',
			sizeRange: [0, 100],
			sizeUnits: 'km²',
			heatIntensityRange: [0, 0],
			heatIntensityUnits: '+°C',
			coldIntensityRange: [0, 0],
			coldIntensityUnits: '-°C',
			durationP90: null,
			sizeP90: null,
			heatIntensityP90: null,
			coldIntensityP90: null,
			eventTypeMode: 'hot',
			eventSetsLoaded: 0,
			filters: {
				duration: {
					minimum: true,
					value: 3,
				},
				size: {
					minimum: true,
					value: 0,
				},
				heatIntensity: {
					minimum: true,
					type: 'max',
					value: 28,
					active: true,
				},
				coldIntensity: {
					minimum: false,
					type: 'mean',
					value: 2,
					active: false,
				},
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
			return (event: ExtremeEvent | ExtremeEventFull | null) => {
				if (!event || !event.hasOwnProperty('max_values')) return []
				event = event as ExtremeEventFull
				if (event.event_type === 'hot') {
					return event.max_values.map((v) => intensityForValue(v, true))
				} else {
					return event.mean_values.map((v) => intensityForValue(v, false))
				}
			}
		},
		intensitiesForEventStep: (state: State) => {
			return (event: ExtremeEvent | ExtremeEventFull | null, time: Date) => {
				if (!event || !event.hasOwnProperty('values')) return []
				event = event as ExtremeEventFull
				const idx = event.times.findIndex((t) => t === time.getTime())
				if (idx === -1 || idx >= event.values.length) return []
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
		async selectEvent(
			event: ExtremeEvent | ExtremeEventFull | null,
			waitForFullLoad = false,
		) {
			// console.log('EventStore: selecting event', id)
			const mainStore = useMainStore()
			const timeStore = useTimeStore()
			if (event === null) {
				this.selectedEvent = null
				this.selectedEventId = null
				return
			}
			await mainStore.setLoading('Selecting event...')
			mainStore.setEventLoading()
			// if (this.selectedEvent?.id === id) {
			if (this.selectedEventId === event.id) {
				this.selectedEvent = null
				this.selectedEventId = null
				mainStore.setLoadingDone()
			} else {
				// mainStore.setLoading()
				this.selectedEventId = event.id
				this.selectedEvent = event as ExtremeEventFull
				// console.log('Selected event is now', this.selectedEvent, JSON.stringify(event))
				if (!waitForFullLoad) {
					mainStore.setLoadingDone()
				} else {
					mainStore.loadingMessage = 'Downloading event data...'
				}

				// console.log('setting selected event to', id)
				let path = `${DATA_ROOT}events/event-${this.selectedEventId}.json`
				const resp = await fetch(path)
				const eventJson = await resp.json()
				eventJson.id = event.id
				eventJson.times = eventJson.times.map((time: string) =>
					new Date(time).getTime(),
				)
				this.selectedEvent = eventJson as ExtremeEventFull
				if (
					timeStore.selectedTime < eventJson.times[0] ||
					timeStore.selectedTime > eventJson.times[event.times.length - 1]
				) {
					timeStore.selectedTime = new Date(event.times[0])
				}
				if (waitForFullLoad) {
					mainStore.setLoadingDone()
				}
				mainStore.setEventLoadingDone()
			}
		},
		setHoveringEvent(event: ExtremeEvent | null) {
			this.hoveringEvent = event
			// console.log('Hovering event set to', event, event?.total_region)
		},
		async runFilters() {
			// console.log('Running event filters')
			const mainStore = useMainStore()
			await mainStore.setLoading()

			setPostFilters(
				this.filters,
				this.durationForEvent,
				this.intensityForEvent,
				this.sizeForEvent,
			)
			// This needs to get set by the leaflet layers
			mainStore.setLoadingDone()
		},
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
			timeStore.startTimeFilter = new Date(Date.UTC(from, 0, 1))
			timeStore.endTimeFilter = new Date(Date.UTC(to, 11, 31))

			onGlobalEventsReady(() => {
				const events = getGlobalFilteredEvents()
				if (events.length > 0) {
					if (!this.firstEventSetLoaded) {
						this.firstEventSetLoaded = true
						// console.log('First event set loaded, clearing loading state')
						mainStore.setLoadingDone()
						setTimeout(() => {
							mainStore.showInfoPanel = true
						}, 1500)
					} else {
						// console.log('Setting loading...')
						// mainStore.setLoading()
					}
				}
				const K = Math.ceil(0.1 * events.length)
				const pushTop = (arr: Array<number>, v: number) => {
					arr.push(v)
					if (arr.length > K) {
						// drop smallest → keep the top K largest values
						arr.sort((a, b) => b - a)
						arr.length = K
					}
				}
				const durationTop: number[] = []
				const sizeTop: number[] = []
				const heatTop: number[] = []
				const coldTop: number[] = []
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

					pushTop(durationTop, duration)
					pushTop(sizeTop, size)
					if (e.event_type === 'hot') pushTop(heatTop, intensity)
					else pushTop(coldTop, intensity)
				})
				this.durationP90 = durationTop.length ? Math.min(...durationTop) : null
				this.sizeP90 = sizeTop.length ? Math.min(...sizeTop) : null
				this.heatIntensityP90 = heatTop.length ? Math.min(...heatTop) : null
				this.coldIntensityP90 = coldTop.length ? Math.min(...coldTop) : null
			})

			// Load hot and cold events
			await fetchAndIndexEvents(['hot', 'cold'], from, to)
		},
	},
})

export type EventStore = ReturnType<typeof useStore>
