import scssVars from '@/assets/styles/scssVars.module.scss'
import {
	fetchAndIndexEvents,
	getParameterFilteredEvents,
	onParameterFilterChanged,
	setParameterFilters,
} from '@/lib/eventsDB'
import {
	applyTheme,
	DATA_ROOT,
	eventTypesForMode,
	interpolateColorCold,
	interpolateColorHot,
	interpolateColorWet,
} from '@/lib/utils'
import * as d3 from 'd3'
import { defineStore } from 'pinia'
import { markRaw, watch } from 'vue'
import { usePersistentStore } from './persistentStore'
import { useStore as useMainStore } from './store'
import { useStore as useTimeStore } from './timeStore'

interface State {
	selectedEvent: ExtremeEventFull | null
	selectedEventId: string | null
	hoveringEvent: ExtremeEvent | null

	heatDurationRange: [number, number]
	coldDurationRange: [number, number]
	wetDurationRange: [number, number]
	durationUnits: string
	heatSizeRange: [number, number]
	coldSizeRange: [number, number]
	wetSizeRange: [number, number]
	sizeUnits: string
	heatIntensityRange: [number, number]
	heatIntensityUnits: string
	coldIntensityRange: [number, number]
	coldIntensityUnits: string
	wetIntensityRange: [number, number]
	wetIntensityUnits: string
	durationP90: number | null
	sizeP90: number | null
	heatIntensityP90: number | null
	coldIntensityP90: number | null
	wetIntensityP90: number | null

	eventTypeMode: SelectedEventType

	eventSetsLoaded: number

	filters: Filters
	firstEventSetLoaded: boolean
}

export const intensityForValue = (v: number, temperature: boolean) => {
	if (v == null || isNaN(v)) return 0
	return v - (temperature ? 273.15 : 0)
}

export const colorForValue = (
	v: number,
	type: EventType,
	scale: d3.ScaleLinear<number, number>,
): string => {
	// if (!event || !scale) return (v: number) => 'transparent'
	if (type === 'hot') {
		return interpolateColorHot(scssVars.c3sred)(scale(v))
	} else if (type === 'cold') {
		return interpolateColorCold(scssVars.c3sblue)(scale(v))
	} else {
		return interpolateColorWet(scssVars.c3steal)(scale(v))
	}
}

export const colorForEvent = (
	event: ExtremeEvent,
	scale: d3.ScaleLinear<number, number>,
) => {
	const value = intensityForValue(
		event.event_type === 'hot'
			? event.max_value
			: event.event_type === 'cold'
				? event.min_value
				: event.mean_value,
		event.event_type === 'hot' || event.event_type === 'cold',
	)
	// console.log(
	// 	'intensity for event',
	// 	event.id,
	// 	'is',
	// 	value,
	// 	intensityForValue,
	// 	colorForValue,
	// )
	return colorForValue(value, event.event_type, scale)
}

export const useStore = defineStore('events', {
	state: (): State => {
		return {
			selectedEvent: null,
			selectedEventId: null,
			hoveringEvent: null,
			heatDurationRange: [3, 14],
			coldDurationRange: [3, 14],
			wetDurationRange: [3, 14],
			durationUnits: 'days',
			heatSizeRange: [0, 100],
			coldSizeRange: [0, 100],
			wetSizeRange: [0, 100],
			sizeUnits: 'km²',
			heatIntensityRange: [28, 40],
			heatIntensityUnits: '°C',
			coldIntensityRange: [-20, 0],
			coldIntensityUnits: '°C',
			wetIntensityRange: [0, 2],
			wetIntensityUnits: 'WDI',
			durationP90: null,
			sizeP90: null,
			heatIntensityP90: null,
			coldIntensityP90: null,
			wetIntensityP90: null,
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
					active: false,
				},
				coldIntensity: {
					minimum: false,
					type: 'min',
					value: 0,
					active: false,
				},
				wetIntensity: {
					minimum: true,
					value: 0,
					active: true,
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
			} else if (state.eventTypeMode === 'wet') {
				return state.wetDurationRange
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
			} else if (state.eventTypeMode === 'wet') {
				return state.wetSizeRange
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
			} else if (state.eventTypeMode === 'wet') {
				return state.wetIntensityRange
			} else {
				return [0, 1]
			}
		},
		intensityUnits: (state: State) => {
			if (state.eventTypeMode === 'hot') {
				return state.heatIntensityUnits
			} else if (state.eventTypeMode === 'cold') {
				return state.coldIntensityUnits
			} else if (state.eventTypeMode === 'wet') {
				return state.wetIntensityUnits
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
		wetScale: (state: State) => {
			return d3
				.scaleLinear()
				.domain(state.wetIntensityRange)
				.range([0, 1])
				.clamp(true)
		},
		colorForEvent: (state: State) => {
			// TODO Logic for configurable intensity definition.
			return (event: ExtremeEvent | ExtremeEventFull) => {
				return colorForValue(
					// @ts-ignore - this is a getter
					state.intensityForEvent(event),
					event.event_type,
					event.event_type === 'hot'
						? // @ts-ignore - these are getters
							state.hotScale
						: event.event_type === 'cold'
							? // @ts-ignore - these are getters
								state.coldScale
							: // @ts-ignore - these are getters
								state.wetScale,
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
					event.event_type === 'hot'
						? event.max_value
						: event.event_type === 'cold'
							? event.min_value
							: event.mean_value,
					event.event_type === 'hot' || event.event_type === 'cold',
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
				if (event.event_type === 'hot' || event.event_type === 'cold') {
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
				if (event.event_type === 'hot' || event.event_type === 'cold') {
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
				const eventDir = event.provisional ? 'events-current' : 'events'
				let path = `${DATA_ROOT}${eventDir}/event-${this.selectedEventId}.json`
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
		async setEventTypeMode(mode: SelectedEventType | null = null) {
			const mainStore = useMainStore()
			const next = mode || 'hot'
			// Selection first. setLoading waits two animation frames for the
			// overlay to paint, so calling it before this left every control
			// bound to the mode looking dead for the length of that wait.
			this.eventTypeMode = next
			// One frame's grace so the pressed state is on screen before the
			// theme starts shifting, then the reload behind the overlay.
			await new Promise((resolve) => requestAnimationFrame(resolve))
			const rainbow = usePersistentStore().rainbowMode
			applyTheme(rainbow ? `${next}-sparkle` : next)
			await mainStore.setLoading('Changing event type...')
			this.filters.heatIntensity.active =
				next === 'hot' || next === 'hotcold' || next === 'hotwet'
			this.filters.coldIntensity.active =
				next === 'cold' || next === 'hotcold' || next === 'coldwet'
			this.filters.wetIntensity.active =
				next === 'wet' || next === 'hotwet' || next === 'coldwet'
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

			// The event catalogue and the background map tiles are served from the
			// same host (see DATA_ROOT). If that host is unreachable, the worker's
			// fetch resolves to an empty catalogue rather than throwing, so it never
			// reaches the `events.length > 0` branch below that clears the loading
			// overlay. Without a fallback, a network failure at startup leaves the
			// overlay up forever with the app otherwise unusable behind it.
			const loadTimeoutMs = 20000
			const loadTimeout = window.setTimeout(() => {
				if (this.firstEventSetLoaded) return
				console.error(
					`No event data arrived within ${loadTimeoutMs / 1000}s of startup ` +
						`(check network connectivity to ${DATA_ROOT}); dismissing the ` +
						'loading overlay so the app remains usable.',
				)
				this.firstEventSetLoaded = true
				mainStore.setLoadingDone()
			}, loadTimeoutMs)

			const rainbow = usePersistentStore().rainbowMode
			applyTheme(rainbow ? `${this.eventTypeMode}-sparkle` : this.eventTypeMode)
			watch(() => [this.filters], this.runFilters, {
				deep: true,
				immediate: false,
			})

			// Hard-code start date, get end date from current year.
			const timeStore = useTimeStore()
			const from = 1979
			const to = new Date().getUTCFullYear()
			timeStore.startTime = new Date(Date.UTC(from, 0, 1))
			timeStore.endTime = new Date(Date.now() - 9 * 24 * 60 * 60 * 1000)//new Date(Date.UTC(to, 11, 31))
			timeStore.startTimeFilter = new Date(
				Date.UTC(Math.max(to - 10, from), 0, 1),
			)
			timeStore.endTimeFilter = new Date(Date.UTC(to, 11, 31))
			timeStore.selectedTime = new Date(Date.now() - 9 * 24 * 60 * 60 * 1000)

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
						clearTimeout(loadTimeout)
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
				const wetTop: number[] = []

				let localHeatMin = Infinity
				let localColdMin = Infinity
				let localHeatMax = -Infinity
				let localColdMax = -Infinity
				let localWetMin = Infinity
				let localWetMax = -Infinity
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
					} else if (e.event_type === 'wet') {
						if (duration < this.wetDurationRange[0]) {
							this.wetDurationRange[0] = duration
						}
						if (duration > this.wetDurationRange[1]) {
							this.wetDurationRange[1] = duration
						}
						if (size < this.wetSizeRange[0]) {
							this.wetSizeRange[0] = size
						}
						if (size > this.wetSizeRange[1]) {
							this.wetSizeRange[1] = size
						}
						if (intensity < localWetMin) {
							localWetMin = intensity
						}
						if (intensity > localWetMax) {
							localWetMax = intensity
						}
					}

					pushTop(durationTop, duration)
					pushTop(sizeTop, size)
					if (e.event_type === 'hot') pushTop(heatTop, intensity)
					else if (e.event_type === 'cold') pushTop(coldTop, intensity)
					else if (e.event_type === 'wet') pushTop(wetTop, intensity)
				})
				durationTop.sort()
				this.durationP90 = durationTop.length
					? durationTop[Math.floor(0.95 * durationTop.length)]
					: null
				this.sizeP90 = sizeTop.length ? Math.min(...sizeTop) : null
				this.heatIntensityP90 = heatTop.length ? Math.min(...heatTop) : null
				this.coldIntensityP90 = coldTop.length ? Math.min(...coldTop) : null
				this.wetIntensityP90 = wetTop.length ? Math.min(...wetTop) : null
				this.heatIntensityRange = [
					localHeatMin === Infinity ? 0 : localHeatMin,
					localHeatMax === -Infinity ? 0 : localHeatMax,
				]
				this.coldIntensityRange = [
					localColdMin === Infinity ? 0 : localColdMin,
					localColdMax === -Infinity ? 0 : localColdMax,
				]
				// It's an index - always start at 0
				this.wetIntensityRange = [
					localWetMin === Infinity ? 0 : localWetMin,
					localWetMax === -Infinity ? 0 : localWetMax,
				]
			})

			// Load the types the user can see first, then the rest in the
			// background. eventTypeMode is read here rather than assumed to be the
			// default, so a mode carried over from a previous visit is honoured.
			await fetchAndIndexEvents(
				['hot', 'cold', 'wet'],
				from,
				to,
				eventTypesForMode(this.eventTypeMode),
			)
		},
	},
})

export type EventStore = ReturnType<typeof useStore>
