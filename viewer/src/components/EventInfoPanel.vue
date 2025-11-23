<script setup>
import { computed, ref } from 'vue'
import { useLabels } from '@/lib/labels'
import { format } from 'date-fns'
import {
	IconAward,
	IconCalendar,
	IconClockHour4,
	IconDimensions,
	IconDownload,
	IconSortAscendingSmallBig,
	IconSortDescendingSmallBig,
	IconStopwatch,
	IconTemperature,
	IconTemperatureSnow,
	IconTemperatureSun,
} from '@tabler/icons-vue'
import { dayStr } from '@/lib/time-utils'
import EventRanker from './util/EventRanker.vue'

const $l = useLabels()

const props = defineProps({
	selectedEvent: {
		type: Object,
		required: false,
	},
	eventStore: {
		type: Object,
		required: true,
	},
	timeString: {
		type: String,
		required: true,
	},
	eventsOfInterest: {
		type: Array,
		required: true,
	},
})

// Format helpers
const timeRange = computed(() => {
	if (!props.selectedEvent?.times?.length) return '—'
	const start = new Date(props.selectedEvent.times[0])
	const end = new Date(props.selectedEvent.times.at(-1))
	if (start.getMonth() === end.getMonth()) {
		return `${format(start, 'dd')} → ${format(end, 'dd MMM')}`
	}
	return `${format(start, 'dd MMM')} → ${format(end, 'dd MMM')}`
	// return `${start.toLocaleDateString()} → ${end.toLocaleDateString()}`
})

const downloadEvent = () => {
	const url = props.eventStore.downloadLinkForEvent(props.selectedEvent)
	const filename = `event_${props.selectedEvent?.id || 'data'}.json`

	const a = document.createElement('a')
	a.href = url
	a.download = filename
	document.body.appendChild(a)
	a.click()
	document.body.removeChild(a)
}

const sortDesc = ref(true)
const toggleAscDesc = () => {
	sortDesc.value = !sortDesc.value
}
const sortModes = ['duration', 'size', 'intensity']
const mode = ref(sortModes[1])
const currentSortMode = ref(1)
const cycleSorts = () => {
	currentSortMode.value = (currentSortMode.value + 1) % sortModes.length
	mode.value = sortModes[currentSortMode.value]
}
const sortFunc = computed(() => {
	const mode = sortModes[currentSortMode.value]
	return sortDesc.value
		? (a, b) => {
				let res = 0
				if (mode === 'duration') {
					res =
						props.eventStore.durationForEvent(b) -
						props.eventStore.durationForEvent(a)
				} else if (mode === 'size') {
					res =
						props.eventStore.sizeForEvent(b) - props.eventStore.sizeForEvent(a)
				} else if (mode === 'intensity') {
					res =
						props.eventStore.intensityForEvent(b) -
						props.eventStore.intensityForEvent(a)
				}
				return res
			}
		: (a, b) => {
				let res = 0
				if (mode === 'duration') {
					res =
						props.eventStore.durationForEvent(b) -
						props.eventStore.durationForEvent(a)
				} else if (mode === 'size') {
					res =
						props.eventStore.sizeForEvent(b) - props.eventStore.sizeForEvent(a)
				} else if (mode === 'intensity') {
					res =
						props.eventStore.intensityForEvent(b) -
						props.eventStore.intensityForEvent(a)
				}
				return -res
			}
})
</script>

<template>
	<div class="event-info panel">
		<div class="info-row title">
			<IconCalendar />
			<span class="value mono">{{ timeString }}</span>
		</div>
		<div class="info-row header">
			<div class="label">
				<IconTemperatureSun v-if="eventStore.eventTypeMode === 'hot'" />
				<IconTemperatureSnow v-else-if="eventStore.eventTypeMode === 'cold'" />
				<IconTemperature v-else />
				<span class="value">{{ eventsOfInterest.length.toLocaleString() }}</span>
			</div>
		</div>
		<div class="buttons">
			<span class="award"
				><IconAward /> {{ eventsOfInterest.length < 100 ? '' : '100' }}
			</span>
			<button @click="cycleSorts" class="cycle-sort-button glassy">
				<IconStopwatch v-if="mode === 'duration'" />
				<IconDimensions v-else-if="mode === 'size'" />
				<IconTemperature v-else />
			</button>
			<button @click="toggleAscDesc" class="cycle-sort-button glassy">
				<IconSortDescendingSmallBig v-if="sortDesc" />
				<IconSortAscendingSmallBig v-else />
			</button>
		</div>
		<div class="info-row">
			<div class="medals-carousel">
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="sortFunc"
					:topN="100"
					:nRowsToShow="8"
				/>
			</div>
		</div>
		<div class="info-row" v-if="props.selectedEvent">
			<IconClockHour4 class="icon" />
			<!-- <span class="label">{{ $l.duration }}:</span> -->
			<span class="value mono"
				>{{ props.eventStore.durationForEvent(props.selectedEvent) }} days
				<span class="small mono">({{ timeRange }})</span></span
			>
		</div>
		<div class="info-row" v-if="props.selectedEvent">
			<IconDimensions class="icon" />
			<!-- <span class="label">{{ $l.size }}:</span> -->
			<span class="value mono"
				>{{
					props.eventStore.sizeForEvent(props.selectedEvent).toFixed(2)
				}}km²</span
			>
		</div>
		<div class="info-row" v-if="props.selectedEvent">
			<IconTemperature class="icon" />
			<!-- <span class="label">{{ $l.intensity }}:</span> -->
			<span class="value mono"
				>+{{
					props.eventStore.intensityForEvent(props.selectedEvent).toFixed(2)
				}}°C</span
			>
		</div>
		<div class="info-row" v-if="props.selectedEvent">
			<div class="download-link" @click="downloadEvent" role="button">
				<IconDownload class="icon" />
			</div>
		</div>
		<slot></slot>
	</div>
</template>

<style scoped>
.download-link {
	cursor: pointer;
	&:hover {
		opacity: 0.8;
	}
}

.event-info {
	display: flex;
	flex-direction: column;
	gap: 0.125rem 1rem;
	padding: 0 0.25rem;
	font-size: 0.75rem;
	justify-content: space-around;
	position: relative;
	z-index: 0;
}

.buttons {
	overflow: visible;
	width: 100%;
	flex: 0 0 1rem;
	max-height: 0 !important;
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
	gap: 0.25rem;
	margin: 0.25rem 0;
	position: relative;
	button {
		/* position: absolute; */
		height: 1.75rem;
		width: 1.75rem;
		.tabler-icon {
			width: 1.5rem;
			height: 1.5rem;
		}
		box-shadow: none !important;
	}
	padding-top: 1.5rem;
	padding-bottom: 0.5rem;
	border-top: 1px solid var(--divider);

	.award {
		margin-right: auto;
		font-size: 1.1rem;
		display: flex;
		align-items: center;
	}
	z-index: 20;
}
.info-row {
	display: flex;
	gap: 0.25rem;
	justify-content: flex-start;
	align-items: center;
	width: 100%;
	overflow: hidden;
	z-index: 5;

	&.header,
	&.title {
		flex-shrink: 0;
		flex-basis: auto;
		font-size: 1.1rem;
		display: flex;
		justify-content: center;
		padding: 0.25rem;
		.tabler-icon {
			width: 2rem;
		}
	}

	&.header {
		position: relative;
		z-index: 10;
		.label {
			/* margin-bottom: 0.5rem; */
			font-size: 1.5rem;
			font-weight: bold;
			display: flex;
			align-items: center;
			/* position: absolute;
			left: 50%;
			transform: translateX(-50%); */
		}
	}

	.medals-carousel {
		z-index: 5;
		/* overflow: hidden; */
		width: 100%;
		/* height: 100%; */
		/* flex-grow: 1; */
		display: flex;
		flex-direction: row;
		/* align-items: stretch; */
		justify-content: center;

		.event-ranker-root {
			flex: 1 1 34%;
			overflow: hidden;
			/* This is 10 events at 24px each - see ROW_HEIGHT in EventRanker.vue */
			height: 160px;
			z-index: 7;
		}
	}
}

.icon {
	color: var(--text-primary);
	width: 1rem;
	margin-right: 0.5rem;
}

.label {
	font-weight: 600;
	flex-shrink: 0;
	text-wrap: nowrap;
	/* min-width: 3.5rem; */
}

.value {
	flex-grow: 1;
	text-align: left;
	text-wrap: nowrap;
	color: var(--text-primary);

	.small {
		font-size: 0.7rem;
		color: var(--text-secondary);
		margin-left: 0.25rem;
	}
}

.cycle-sort-button {
	padding: 0.125rem;
	margin: 0;
	cursor: pointer;
	box-shadow: none;

	.tabler-icon {
		width: 1rem;
		color: var(--text-primary);
	}
}
</style>
