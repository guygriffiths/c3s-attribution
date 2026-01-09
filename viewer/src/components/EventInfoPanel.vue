<script setup lang="ts">
import { computed, ref } from 'vue'
import { format } from 'date-fns'
import {
	IconAward,
	IconDimensions,
	IconSortAscendingSmallBig,
	IconSortDescendingSmallBig,
	IconStopwatch,
	IconTemperature,
	IconTemperatureSnow,
	IconTemperatureSun,
} from '@tabler/icons-vue'
import EventRanker from './util/EventRanker.vue'
import CalendarIcon from './util/CalendarIcon.vue'
import { useLabels } from '@/lib/labels'

const $l = useLabels()

const props = defineProps<{
	selectedEvent: ExtremeEvent | ExtremeEventFull | null
	mainStore: any
	eventStore: any
	timeStore: any
	eventsOfInterest: ExtremeEvent[]
}>()

const timeString = computed(() =>
	props.mainStore.viewMode === 'timemachine'
		? format(props.timeStore.selectedTime, 'dd MMM yy')
		: format(props.timeStore.startTimeFilter, 'MMM yy') +
			' - ' +
			format(props.timeStore.endTimeFilter, 'MMM yy'),
)
const dateNumber = computed(() => {
	return props.mainStore.viewMode === 'timemachine'
		? props.timeStore.selectedTime.getUTCDate()
		: null
})
const toggleAscDesc = () => {
	props.mainStore.sortDesc = !props.mainStore.sortDesc
}
const sortFunc = computed(() => {
	if (props.mainStore.sortDesc) {
		if (props.mainStore.focusVariable === 'duration') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.durationForEvent(b) -
				props.eventStore.durationForEvent(a)
		} else if (props.mainStore.focusVariable === 'size') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.sizeForEvent(b) - props.eventStore.sizeForEvent(a)
		} else if (props.mainStore.focusVariable === 'intensity') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.intensityForEvent(b) -
				props.eventStore.intensityForEvent(a)
		}
	} else {
		if (props.mainStore.focusVariable === 'duration') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.durationForEvent(a) -
				props.eventStore.durationForEvent(b)
		} else if (props.mainStore.focusVariable === 'size') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.sizeForEvent(a) - props.eventStore.sizeForEvent(b)
		} else if (props.mainStore.focusVariable === 'intensity') {
			return (a: ExtremeEvent, b: ExtremeEvent) =>
				props.eventStore.intensityForEvent(a) -
				props.eventStore.intensityForEvent(b)
		}
	}
	return () => 0
})
</script>

<template>
	<div class="event-info panel">
		<div
			class="info-row header"
			v-tooltip="
				eventsOfInterest.length.toLocaleString() +
				' ' +
				(eventStore.eventTypeMode === 'hot'
					? $l.heatwaveEvents
					: eventStore.eventTypeMode === 'cold'
						? $l.coldwaveEvents
						: $l.allTemperatureEvents)
			"
		>
			<div class="label">
				<IconTemperatureSun
					v-if="eventStore.eventTypeMode === 'hot'"
					aria-hidden="true"
				/>
				<IconTemperatureSnow
					v-else-if="eventStore.eventTypeMode === 'cold'"
					aria-hidden="true"
				/>
				<IconTemperature v-else aria-hidden="true" />
				<span class="value" aria-hidden="true">{{
					eventsOfInterest.length.toLocaleString()
				}}</span>
			</div>
		</div>
		<div class="info-row title">
			<CalendarIcon :size="24" :date="dateNumber" aria-hidden="true" />
			<span class="value mono">{{ timeString }}</span>
		</div>
		<div class="buttons">
			<span
				class="award"
				v-tooltip="
					eventsOfInterest.length < 100
						? $l.rankingForTopEvents
						: $l.rankingForTop100Events
				"
				><IconAward /> {{ eventsOfInterest.length < 100 ? '' : '100' }}
			</span>
			<button
				@click="props.mainStore.cycleSorts"
				class="cycle-sort-button glassy"
				v-tooltip="
					(mainStore.focusVariable === 'duration'
						? $l.rankedByDuration
						: mainStore.focusVariable === 'size'
							? $l.rankedBySize
							: $l.rankedByIntensity) +
					' (' +
					$l.cycleSortVariable +
					')'
				"
			>
				<IconStopwatch
					v-if="mainStore.focusVariable === 'duration'"
					aria-hidden="true"
				/>
				<IconDimensions
					v-else-if="mainStore.focusVariable === 'size'"
					aria-hidden="true"
				/>
				<IconTemperature v-else aria-hidden="true" />
			</button>
			<button
				@click="toggleAscDesc"
				class="cycle-sort-button glassy"
				v-tooltip="props.mainStore.sortDesc ? $l.sortAscending : $l.sortDescending"
			>
				<IconSortDescendingSmallBig v-if="props.mainStore.sortDesc" aria-hidden="true" />
				<IconSortAscendingSmallBig v-else aria-hidden="true" />
			</button>
		</div>
		<div class="info-row">
			<div class="ranker-container">
				<EventRanker
					:events="eventsOfInterest"
					:sort-func="sortFunc"
					:topN="100"
					:nRowsToShow="8"
				/>
			</div>
		</div>
		<slot />
	</div>
</template>

<style>
/* Remove the inner details of the calendar icon to make space for the date number */
.calendar-frame > path:nth-child(5),
.calendar-frame > path:nth-child(6) {
	display: none !important;
	opacity: 0 !important;
}
</style>

<style scoped>
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
		user-select: none;

		.tabler-icon {
			width: 2rem;
		}

		.date-text {
			/* Position the icon in the calendar icon */
			position: absolute;
			left: calc(0.25rem + 20px);
			transform: translate(-50%, 4px);
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

	.ranker-container {
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
			flex: 0 0 100%;
			overflow: hidden;
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
</style>
