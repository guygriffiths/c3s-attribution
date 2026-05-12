<script setup lang="ts">
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import Histogram from './util/Histogram.vue'
import ScatterPlot from './util/ScatterPlot.vue'
import {
	IconLayersIntersect,
	IconStopwatch,
	IconDimensions,
	IconTemperature,
	IconCalendar,
	IconArrowsDiagonal,
	IconZoomScan,
	IconViewfinder,
	IconCloudRain,
} from '@tabler/icons-vue'
import { ref, watch, computed } from 'vue'
import { getBins } from '@/lib/histo-utils'
import { niceNumber } from '@/lib/utils'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
const store = useStore()
const eventStore = useEventStore()
const timeStore = useTimeStore()
const scrollerRef = ref<HTMLElement | null>(null)
const scatterSubRef = ref<HTMLElement | null>(null)

const props = defineProps<{
	eventsOfInterest: ExtremeEvent[]
	backgroundEvents?: ExtremeEvent[]
	selectedEvent: ExtremeEventFull | ExtremeEvent | null
}>()

// console.log('TODO: scrollTo on resize, MultiEventPanel')
watch(
	() => store.showAnalytics,
	(newVal) => {
		if (newVal) {
			scatterSubRef.value?.scrollIntoView({
				behavior: 'smooth',
				block: 'start',
			})
			// scrollerRef.value?.scrollTo({ top: scrollerRef.value.scrollHeight, behavior: 'smooth' })
		} else {
			// medalsSubRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
			scrollerRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
		}
	},
)

const minVar = (focus: string, axisMode: string) => {
	return axisMode === 'event' && eventStore.selectedEvent
		? focus === 'duration'
			? eventStore.durationForEvent(eventStore.selectedEvent) * 0.9
			: focus === 'size'
				? eventStore.sizeForEvent(eventStore.selectedEvent) * 0.9
				: eventStore.intensityForEvent(eventStore.selectedEvent) * 0.9
		: focus === 'duration'
			? eventStore.durationRange[0]
			: focus === 'size'
				? eventStore.sizeRange[0]
				: eventStore.intensityRange[0]
}
const xmin = computed(() => {
	return minVar(store.focusVariable, store.axisMode)
})
const ymin = computed(() => {
	return minVar(scatterY.value, store.axisMode)
})
const maxVar = (focus: string, axisMode: string) => {
	return focus === 'duration'
		? axisMode === 'full'
			? eventStore.durationRange[1]
			: axisMode === 'most'
				? eventStore.durationP90 || eventStore.durationRange[1]
				: axisMode === 'event' && eventStore.selectedEvent
					? eventStore.durationForEvent(eventStore.selectedEvent) * 1.1
					: eventStore.durationP90 || eventStore.durationRange[1]
		: focus === 'size'
			? axisMode === 'full'
				? eventStore.sizeRange[1]
				: axisMode === 'most'
					? eventStore.sizeP90 || eventStore.sizeRange[1]
					: axisMode === 'event' && eventStore.selectedEvent
						? eventStore.sizeForEvent(eventStore.selectedEvent) * 1.1
						: eventStore.sizeP90 || eventStore.sizeRange[1]
			: axisMode === 'full'
				? eventStore.intensityRange[1]
				: axisMode === 'most'
					? Math.max(
							eventStore.heatIntensityP90 || 0,
							eventStore.coldIntensityP90 || 0,
						)
					: axisMode === 'event' && eventStore.selectedEvent
						? eventStore.intensityForEvent(eventStore.selectedEvent) * 1.1
						: Math.max(
								eventStore.heatIntensityP90 || 0,
								eventStore.coldIntensityP90 || 0,
							)
}
const xmax = computed(() => {
	return maxVar(store.focusVariable, store.axisMode)
})
const ymax = computed(() => {
	return maxVar(scatterY.value, store.axisMode)
})

const valueForEvent = computed(() => {
	if (!eventStore.selectedEvent) return null
	return store.focusVariable === 'duration'
		? eventStore.durationForEvent(eventStore.selectedEvent)
		: store.focusVariable === 'size'
			? eventStore.sizeForEvent(eventStore.selectedEvent)
			: eventStore.intensityForEvent(eventStore.selectedEvent)
})
const eventsOfInterest = computed(() => {
	return store.focusVariable === 'duration'
		? props.eventsOfInterest.map(eventStore.durationForEvent)
		: store.focusVariable === 'size'
			? props.eventsOfInterest.map(eventStore.sizeForEvent)
			: props.eventsOfInterest.map(eventStore.intensityForEvent)
})
const backgroundEvents = computed(() => {
	return props.backgroundEvents
		? store.focusVariable === 'duration'
			? props.backgroundEvents.map(eventStore.durationForEvent)
			: store.focusVariable === 'size'
				? props.backgroundEvents.map(eventStore.sizeForEvent)
				: props.backgroundEvents.map(eventStore.intensityForEvent)
		: []
})
const backgroundEventsY = computed(() => {
	if (!props.backgroundEvents) return []
	return scatterY.value === 'intensity'
		? props.backgroundEvents.map((e) => eventStore.intensityForEvent(e))
		: scatterY.value === 'duration'
			? props.backgroundEvents.map((e) => eventStore.durationForEvent(e))
			: props.backgroundEvents.map((e) => eventStore.sizeForEvent(e))
})

const types = computed(() => {
	return props.eventsOfInterest.map((e) => e.event_type)
})
const scatterY = ref<Variable>('intensity')
const cycleYVar = () => {
	// if (scatterY.value === 'intensity') {
	// 	scatterY.value = 'duration'
	// } else if (scatterY.value === 'duration') {
	// 	scatterY.value = 'size'
	// } else {
	// 	scatterY.value = 'intensity'
	// }
	if (scatterY.value === 'intensity') {
		if (store.focusVariable === 'duration') scatterY.value = 'size'
		else scatterY.value = 'duration'
	} else if (scatterY.value === 'duration') {
		if (store.focusVariable === 'size') scatterY.value = 'intensity'
		else scatterY.value = 'size'
	} else {
		if (store.focusVariable === 'intensity') scatterY.value = 'duration'
		else scatterY.value = 'intensity'
	}
}
watch(
	() => store.focusVariable,
	() => {
		// ensure scatterY is not the same as focusVariable
		if (scatterY.value === store.focusVariable) {
			cycleYVar()
		}
	},
)
const ydata = computed(() => {
	return scatterY.value === 'intensity'
		? props.eventsOfInterest.map((e) => eventStore.intensityForEvent(e))
		: scatterY.value === 'duration'
			? props.eventsOfInterest.map((e) => eventStore.durationForEvent(e))
			: props.eventsOfInterest.map((e) => eventStore.sizeForEvent(e))
})
const selectedX = computed(() => {
	if (!eventStore.selectedEvent) return null
	return store.focusVariable === 'duration'
		? eventStore.durationForEvent(eventStore.selectedEvent)
		: store.focusVariable === 'size'
			? eventStore.sizeForEvent(eventStore.selectedEvent)
			: eventStore.intensityForEvent(eventStore.selectedEvent)
})
const selectedY = computed(() => {
	if (!eventStore.selectedEvent) return null
	return scatterY.value === 'intensity'
		? eventStore.intensityForEvent(eventStore.selectedEvent)
		: scatterY.value === 'duration'
			? eventStore.durationForEvent(eventStore.selectedEvent)
			: eventStore.sizeForEvent(eventStore.selectedEvent)
})
const ids = computed(() => {
	return props.eventsOfInterest.map((e) => e.id)
})
const bins = computed(() => {
	const data = eventsOfInterest.value
	return getBins(
		data,
		types.value,
		xmin.value,
		xmax.value,
		10,
		store.axisMode !== 'full',
	)
})
const maxCount = computed(() => {
	return bins.value.reduce((max, bin) => Math.max(max, bin.count), 0)
})
watch(
	() => store.focusVariable,
	(newVal, oldVal) => {
		if (scatterY.value === newVal) {
			scatterY.value = oldVal
		}
	},
)

const xscaleFactor = computed(() => {
	// TODO Would be better using 90th%ile or similar
	return 1 / (xmax.value - xmin.value)
})
const yscaleFactor = computed(() => {
	return 1 / (ymax.value - ymin.value)
})

const getXYScatterTitle = computed(() => {
	const xLabel =
		store.focusVariable === 'duration'
			? $l.value.duration
			: store.focusVariable === 'size'
				? $l.value.size
				: eventStore.eventTypeMode === 'wet'
					? $l.value.wetIndex
					: $l.value.temperature
	const yLabel =
		scatterY.value === 'duration'
			? $l.value.duration
			: scatterY.value === 'size'
				? $l.value.size
				: eventStore.eventTypeMode === 'wet'
					? $l.value.wetIndex
					: $l.value.temperature
	return `${yLabel} vs ${xLabel}`
})
</script>
<template>
	<div class="multi-event-panel panel">
		<slot />
		<h3 class="panel-title">{{ $l.multiEventPanelTitle }}</h3>
		<div class="scroller" ref="scrollerRef">
			<div class="chart histo">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">
							{{ 0 }}
						</div>
						<span class="units icon" v-tooltip="$l.nEvents"
							><IconLayersIntersect aria-hidden="true" />{{
								$l.nEventsShort
							}}</span
						>
						<div class="label mono">
							{{ maxCount }}
						</div>
					</div>
					<Histogram
						:data="eventsOfInterest"
						:bins="bins"
						:nbins="10"
						:xmin="xmin"
						:xmax="xmax"
						:labelFunc="(v: number) => v.toFixed(0)"
						:units="'days'"
						:highlight-value="valueForEvent"
						:types="types"
						:has-tail="store.axisMode !== 'full'"
						:title="
							store.focusVariable === 'duration'
								? $l.durationHisto
								: store.focusVariable === 'size'
									? $l.sizeHisto
									: eventStore.eventTypeMode === 'wet'
										? $l.wetHisto
										: $l.tempHisto
						"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono">
						{{ niceNumber(xmin) }}
					</div>
					<span class="units icon">
						<button
							@click="store.cycleSorts"
							class="cycle-sort-button glassy"
							v-tooltip="
								(store.focusVariable === 'duration'
									? $l.duration
									: store.focusVariable === 'size'
										? $l.size
										: eventStore.eventTypeMode === 'wet'
											? $l.wetIndex
											: $l.temperature) +
								' (' +
								$l.cycleSortVariable +
								')'
							"
						>
							<IconStopwatch
								v-if="store.focusVariable === 'duration'"
								aria-hidden="true"
							/>
							<IconDimensions
								v-else-if="store.focusVariable === 'size'"
								aria-hidden="true"
							/>
							<IconTemperature
								v-else-if="eventStore.eventTypeMode !== 'wet'"
								aria-hidden="true"
							/>
							<IconCloudRain v-else aria-hidden="true" />
						</button>
						<span v-if="store.focusVariable === 'duration'">{{
							$l.duration
						}}</span>
						<span v-else-if="store.focusVariable === 'size'">{{
							$l.size
						}}</span>
						<span v-else>{{
							eventStore.eventTypeMode === 'wet' ? $l.wetIndex : $l.temperature
						}}</span>
					</span>
					<div class="label mono">
						{{ niceNumber(xmax) }}
					</div>
				</div>
			</div>
			<div class="chart scatter">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">{{ niceNumber(ymin) }}</div>
						<span class="units icon">
							<button
								@click="cycleYVar"
								class="cycle-sort-button glassy"
								v-tooltip="
									(scatterY === 'duration'
										? $l.duration
										: scatterY === 'size'
											? $l.size
											: eventStore.eventTypeMode === 'wet'
												? $l.wetIndex
												: $l.temperature) +
									' (' +
									$l.cycleSortVariable +
									')'
								"
							>
								<IconStopwatch
									v-if="scatterY === 'duration'"
									aria-hidden="true"
								/>
								<IconDimensions
									v-else-if="scatterY === 'size'"
									aria-hidden="true"
								/>
								<IconTemperature
									v-else-if="eventStore.eventTypeMode !== 'wet'"
									aria-hidden="true"
								/>
								<IconCloudRain v-else aria-hidden="true" />
							</button>
							<span v-if="scatterY === 'duration'">{{ $l.duration }}</span>
							<span v-else-if="scatterY === 'size'">{{ $l.size }}</span>
							<span v-else>{{ eventStore.eventTypeMode === 'wet' ? $l.wetIndex : $l.temperature }}</span>
						</span>
						<div class="label mono">
							{{ niceNumber(ymax) }}
						</div>
					</div>
					<ScatterPlot
						:xdata="eventsOfInterest"
						:ydata="ydata"
						:xbg="backgroundEvents"
						:ybg="backgroundEventsY"
						:types="types"
						:xmin="xmin"
						:xmax="xmax"
						:ymin="ymin"
						:ymax="ymax"
						:xscale="xscaleFactor"
						:yscale="yscaleFactor"
						:ids="ids"
						:selectedX="selectedX"
						:selectedY="selectedY"
						:highlightId="eventStore.selectedEventId"
						:title="getXYScatterTitle"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono">
						{{ niceNumber(xmin) }}
					</div>
					<span class="units icon">
						<button
							@click="store.cycleSorts"
							class="cycle-sort-button glassy"
							v-tooltip="
								(store.focusVariable === 'duration'
									? $l.duration
									: store.focusVariable === 'size'
										? $l.size
										: eventStore.eventTypeMode === 'wet'
											? $l.wetIndex
											: $l.temperature) +
								' (' +
								$l.cycleSortVariable +
								')'
							"
						>
							<IconStopwatch
								v-if="store.focusVariable === 'duration'"
								aria-hidden="true"
							/>
							<IconDimensions
								v-else-if="store.focusVariable === 'size'"
								aria-hidden="true"
							/>
							<IconTemperature
								v-else-if="eventStore.eventTypeMode !== 'wet'"
								aria-hidden="true"
							/>
							<IconCloudRain v-else aria-hidden="true" />
						</button>
						<span v-if="store.focusVariable === 'duration'">{{
							$l.duration
						}}</span>
						<span v-else-if="store.focusVariable === 'size'">{{
							$l.size
						}}</span>
						<span v-else>{{ eventStore.eventTypeMode === 'wet' ? $l.wetIndex : $l.temperature }}</span>
					</span>
					<div class="label mono">
						{{ niceNumber(xmax) }}
					</div>
				</div>
			</div>
			<div class="chart ts">
				<div class="yaxis-chart">
					<div class="axis">
						<div class="label mono">{{ niceNumber(xmin) }}</div>
						<span class="units icon">
							<button
								@click="store.cycleSorts"
								class="cycle-sort-button glassy"
								v-tooltip="
									(store.focusVariable === 'duration'
										? $l.duration
										: store.focusVariable === 'size'
											? $l.size
											: eventStore.eventTypeMode === 'wet'
												? $l.wetIndex
												: $l.temperature) +
									' (' +
									$l.cycleSortVariable +
									')'
								"
							>
								<IconStopwatch
									v-if="store.focusVariable === 'duration'"
									aria-hidden="true"
								/>
								<IconDimensions
									v-else-if="store.focusVariable === 'size'"
									aria-hidden="true"
								/>
								<IconTemperature
									v-else-if="eventStore.eventTypeMode !== 'wet'"
									aria-hidden="true"
								/>
								<IconCloudRain v-else aria-hidden="true" />
							</button>
							<span v-if="store.focusVariable === 'duration'">{{
								$l.duration
							}}</span>
							<span v-else-if="store.focusVariable === 'size'">{{
								$l.size
							}}</span>
							<span v-else>{{ eventStore.eventTypeMode === 'wet' ? $l.wetIndex : $l.temperature }}</span>
						</span>
						<div class="label mono">
							{{ niceNumber(xmax) }}
						</div>
					</div>
					<ScatterPlot
						:xdata="props.eventsOfInterest.map((e) => e.times[0])"
						:ydata="eventsOfInterest"
						:xbg="
							props.backgroundEvents
								? props.backgroundEvents.map((e) => e.times[0])
								: []
						"
						:ybg="backgroundEvents"
						:types="types"
						:xmin="timeStore.startTimeFilter.getTime()"
						:xmax="timeStore.endTimeFilter.getTime()"
						:ymin="xmin"
						:ymax="xmax"
						:ids="ids"
						:selectedX="timeStore.selectedTime.getTime()"
						:selectedY="selectedX"
						:hoverId="eventStore.hoveringEvent?.id"
						:title="
							store.focusVariable === 'duration'
								? $l.durationTimeSeries
								: store.focusVariable === 'size'
									? $l.sizeTimeSeries
									: eventStore.eventTypeMode === 'wet'
										? $l.wetTimeSeries
										: $l.tempTimeSeries
						"
					/>
				</div>
				<div class="axis horizontal">
					<div class="label mono date">
						{{ timeStore.startTimeFilter.toISOString().slice(0, 10) }}
					</div>
					<span class="units icon" v-tooltip="$l.time">
						<IconCalendar aria-hidden="true" />
					</span>
					<div class="label mono date">
						{{ timeStore.endTimeFilter.toISOString().slice(0, 10) }}
					</div>
				</div>
			</div>
		</div>
		<!-- <div class="buttons">
			<IconChartHistogram class="body" size="1.5rem" />
			<IconChartSankey class="tail" size="1.25rem" />
		</div> -->
		<div class="chart-control">
			<button
				class="glassy"
				:class="{ selected: store.axisMode === 'most' }"
				@click="store.axisMode = 'most'"
				v-tooltip="$l.focusOnMostEvents"
			>
				<IconZoomScan aria-hidden="true" />
			</button>
			<button
				class="glassy"
				:class="{ selected: store.axisMode === 'full' }"
				@click="store.axisMode = 'full'"
				v-tooltip="$l.focusOnAllEvents"
			>
				<IconArrowsDiagonal aria-hidden="true" />
			</button>
			<button
				class="glassy"
				:class="{ selected: store.axisMode === 'event' }"
				:disabled="!selectedX"
				@click="store.axisMode = 'event'"
				v-tooltip="$l.focusOnSelectedEvent"
			>
				<IconViewfinder aria-hidden="true" />
			</button>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.buttons {
	position: absolute;
	bottom: 0.5rem;
	right: 0.5rem;
	display: flex;
	flex-direction: row;
	gap: 0rem;
}

.multi-event-panel {
	display: flex;
	flex-direction: column;
	padding: 0.75rem 0.5rem;

	$controlsHeight: 1.5rem;
	.chart-control {
		display: flex;
		flex-direction: row;
		justify-content: center;
		align-items: center;
		padding: 0;
		flex: 0 0 0;
		height: 0;
		overflow: visible;
		position: absolute;
		bottom: 0;
		width: 100%;

		button {
			height: $controlsHeight;

			box-shadow: none !important;
			border-radius: 0;
			&:first-child {
				border-top-left-radius: 0.5rem;
				border-bottom-left-radius: 0.5rem;
			}
			&:last-child {
				border-top-right-radius: 0.5rem;
				border-bottom-right-radius: 0.5rem;
			}
			padding: 0 1rem;

			.tabler-icon {
				width: 90%;
			}
		}
	}

	.scroller {
		height: 100%;
		width: 100%;
		flex: 1 1 auto;

		display: flex;
		flex-direction: column;
		overflow-y: scroll;
		overflow-x: visible;
		// margin-bottom: 0.25rem;
		scroll-snap-type: y mandatory;
		justify-content: space-between;
		position: relative;

		.chart {
			flex: 0 0 calc(100% - 1.5rem);
			// &.histo {
			// 	flex-basis: calc(100% - 1.5rem - $controlsHeight);
			// 	padding-bottom: 2rem;
			// }
			// &.scatter {
			// 	flex-basis: calc(100% - 1.5rem - $controlsHeight);
			// 	padding-top: 2rem;
			// }

			scroll-snap-align: center;
			padding: 0.5rem 1rem 0.25rem 0.25rem;
			border: none;
			// border: 1px solid orange;
			border-bottom: 1px solid var(--divider);
			width: 100%;
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
			justify-content: space-around;

			.yaxis-chart {
				flex: 1 1 auto;
				display: flex;
				flex-direction: row;
				justify-content: space-between;
				gap: 0.5rem;
				align-items: center;
				// border: 1px solid red;
			}

			.axis.horizontal {
				margin-left: 2.5rem;
				width: calc(100% - 2.5rem);
			}

			.axis .label {
				flex: 0 0 1rem;
			}
			.axis.horizontal .label {
				flex: 1 1 33%;

				&.date {
					flex: 1 1 100%;
				}

				&:first-child {
					text-align: left;
				}
				&:last-child {
					text-align: right;
				}
			}
			.axis .icon {
				flex: 1 1 100%;
				flex-direction: column-reverse;
				span {
					writing-mode: vertical-rl;
					transform: rotate(180deg);
				}
			}
			.axis.horizontal .icon {
				flex: 1 1 100%;
				flex-direction: row;

				span {
					writing-mode: horizontal-tb;
					margin-left: 0.25rem;
					transform: none;
				}
			}
			.histogram-root,
			.scatter-root {
				flex: 1 1 auto;
				border: 1px solid var(--divider);
				background: var(--panel-bg);
				padding: 0;
				box-shadow: inset 2px 2px 8px rgba(0, 0, 0, 0.2);
			}
		}
	}
}
</style>
