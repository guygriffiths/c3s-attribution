import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	fetchAndIndexEvents,
	getParameterFilteredEvents,
	onParameterFilterChanged,
	setParameterFilters,
} from '@/lib/eventsDB'
import {
	DATA_ROOT,
	interpolateColorCold,
	interpolateColorHot,
	setTheme,
} from '@/lib/utils'
import * as d3 from 'd3'
import { defineStore } from 'pinia'
import { markRaw, watch } from 'vue'
import { useStore as useMainStore } from './store'
import { useStore as useTimeStore } from './timeStore'

interface State {
	selectedEvent: ExtremeEventFull | null
	selectedEventId: string | null
	hoveringEvent: ExtremeEvent | null

	heatDurationRange: [number, number]
	coldDurationRange: [number, number]
	durationUnits: string
	heatSizeRange: [number, number]
	coldSizeRange: [number, number]
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
	// console.log('intensityForValue', v, hot, v - (hot ? 273.15 : 273.15))
	return v - (hot ? 273.15 : 273.15)
	// if (hot) {
	// 	let baseline = 301.15
	// 	return v - baseline
	// } else {
	// 	let baseline = 275.15
	// 	return baseline - v
	// }
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
		event.event_type === 'hot' ? event.max_value : event.min_value,
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
			heatDurationRange: [3, 14],
			coldDurationRange: [3, 14],
			durationUnits: 'days',
			heatSizeRange: [0, 100],
			coldSizeRange: [0, 100],
			sizeUnits: 'km²',
			heatIntensityRange: [28, 40],
			heatIntensityUnits: '°C',
			coldIntensityRange: [-20, 2],
			coldIntensityUnits: '°C',
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
		durationRange: (state: State) => {
			if (state.eventTypeMode === 'hotcold') {
				return [
					Math.min(state.coldDurationRange[0], state.heatDurationRange[0]),
					Math.max(state.coldDurationRange[1], state.heatDurationRange[1]),
				]
			} else if (state.eventTypeMode === 'hot') {
				return state.heatDurationRange
			} else if (state.eventTypeMode === 'cold') {
				return state.coldDurationRange
			} else {
				return [0, 1]
			}
		},
		sizeRange: (state: State) => {
			if (state.eventTypeMode === 'hotcold') {
				return [
					Math.min(state.coldSizeRange[0], state.heatSizeRange[0]),
					Math.max(state.coldSizeRange[1], state.heatSizeRange[1]),
				]
			} else if (state.eventTypeMode === 'hot') {
				return state.heatSizeRange
			} else if (state.eventTypeMode === 'cold') {
				return state.coldSizeRange
			} else {
				return [0, 1]
			}
		},
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
		intensityUnits: (state: State) => {
			if (state.eventTypeMode === 'hot') {
				return state.heatIntensityUnits
			} else if (state.eventTypeMode === 'cold') {
				return state.coldIntensityUnits
			} else {
				return '°C'
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
				.range([1, 0])
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
				(event?.total_area || 0)
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
				return event.areas || []
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
			// if (this.selectedEvent?.id === id) {
			if (this.selectedEventId === event.id) {
				// this.selectedEvent = null
				// this.selectedEventId = null
				mainStore.setLoadingDone()
				return
			} else {
				mainStore.setEventLoading()
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
				this.selectedEvent = markRaw(eventJson as ExtremeEventFull)
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
		},
		async setEventTypeMode(
			mode: 'hot' | 'cold' | 'hotcold' | null | undefined,
		) {
			const mainStore = useMainStore()
			await mainStore.setLoading('Changing event type...')
			this.eventTypeMode = mode || 'hot'
			setTheme(mode === 'hot' ? 'hot' : mode === 'cold' ? 'cold' : 'hotcold')
			mainStore.setLoadingDone()
		},
		cycleEventType() {
			if (this.eventTypeMode === 'hot') {
				this.setEventTypeMode('cold')
			} else if (this.eventTypeMode === 'cold') {
				this.setEventTypeMode('hotcold')
			} else {
				this.setEventTypeMode('hot')
			}
		},
		async runFilters() {
			const mainStore = useMainStore()
			await mainStore.setLoading()
			setParameterFilters(
				this.filters,
				this.durationForEvent,
				this.sizeForEvent,
				this.intensityForEvent,
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
			const to = new Date().getUTCFullYear()
			timeStore.startTime = new Date(Date.UTC(from, 0, 1))
			timeStore.endTime = new Date(Date.UTC(to, 11, 31))
			timeStore.startTimeFilter = new Date(
				Date.UTC(Math.max(to - 20, from), 0, 1),
			)
			timeStore.endTimeFilter = new Date(Date.UTC(to, 11, 31))
			timeStore.selectedTime = new Date()

			// watch(
			// 	() => [timeStore.startTimeFilter, timeStore.endTimeFilter],
			// 	() => {
			// 		this.refilterEventsDB()
			// 	},
			// 	{ immediate: true },
			// )

			onParameterFilterChanged(() => {
				const events = getParameterFilteredEvents()
				// console.trace('global events ready, count:', events.length)
				// this.refilterEventsDB()
				if (events.length > 0) {
					if (!this.firstEventSetLoaded) {
						this.firstEventSetLoaded = true
						mainStore.setLoadingDone()
						setTimeout(() => {
							mainStore.showInfoPanel = true
						}, 500)
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

				let localHeatMin = Infinity
				let localColdMin = Infinity
				let localHeatMax = -Infinity
				let localColdMax = -Infinity
				events.forEach((e) => {
					const duration = this.durationForEvent(e)

					const size = this.sizeForEvent(e)

					const intensity = this.intensityForEvent(e)
					if (e.event_type === 'hot') {
						if (duration < this.heatDurationRange[0]) {
							this.heatDurationRange[0] = duration
						}
						if (duration > this.heatDurationRange[1]) {
							this.heatDurationRange[1] = duration
						}
						if (size < this.heatSizeRange[0]) {
							this.heatSizeRange[0] = size
						}
						if (size > this.heatSizeRange[1]) {
							this.heatSizeRange[1] = size
						}
						if (intensity < localHeatMin) {
							localHeatMin = intensity
						}
						if (intensity > localHeatMax) {
							localHeatMax = intensity
						}
					} else if (e.event_type === 'cold') {
						if (duration < this.coldDurationRange[0]) {
							this.coldDurationRange[0] = duration
						}
						if (duration > this.coldDurationRange[1]) {
							this.coldDurationRange[1] = duration
						}
						if (size < this.coldSizeRange[0]) {
							this.coldSizeRange[0] = size
						}
						if (size > this.coldSizeRange[1]) {
							this.coldSizeRange[1] = size
						}
						if (intensity < localColdMin) {
							localColdMin = intensity
						}
						if (intensity > localColdMax) {
							localColdMax = intensity
						}
					}

					pushTop(durationTop, duration)
					pushTop(sizeTop, size)
					if (e.event_type === 'hot') pushTop(heatTop, intensity)
					else pushTop(coldTop, intensity)
				})
				durationTop.sort()
				this.durationP90 = durationTop.length
					? durationTop[Math.floor(0.95 * durationTop.length)]
					: null
				this.sizeP90 = sizeTop.length ? Math.min(...sizeTop) : null
				this.heatIntensityP90 = heatTop.length ? Math.min(...heatTop) : null
				this.coldIntensityP90 = coldTop.length ? Math.min(...coldTop) : null
				this.heatIntensityRange = [
					localHeatMin === Infinity ? 0 : localHeatMin,
					localHeatMax === -Infinity ? 0 : localHeatMax,
				]
				this.coldIntensityRange = [
					localColdMin === Infinity ? 0 : localColdMin,
					localColdMax === -Infinity ? 0 : localColdMax,
				]
			})

			// Load hot and cold events
			await fetchAndIndexEvents(['hot', 'cold'], from, to)
		},
	},
})

export type EventStore = ReturnType<typeof useStore>
