<script setup>
import { computed } from 'vue'
import {
	faClock,
	faSignal,
	faFire,
	faMap,
	faExpand,
	faTemperatureHigh,
	faDownload,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { useLabels } from '@/lib/labels'
import { format } from 'date-fns'
import {
	IconClockHour4,
	IconDimensions,
	IconDownload,
	IconTemperature,
	IconTemperatureSun,
} from '@tabler/icons-vue'

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
</script>

<template>
	<div class="event-info">
		<!-- <div class="info-row">
      <FontAwesomeIcon :icon="faClock" class="icon" />
      <span class="label">Debug:</span>
      <span class="value">{{ props.selectedEvent }}</span>
    </div> -->
		<div class="info-row">
			<IconClockHour4 class="icon" />
			<!-- <span class="label">{{ $l.duration }}:</span> -->
			<span class="value"
				>{{ props.eventStore.durationForEvent(props.selectedEvent) }} days
				<span class="small">({{ timeRange }})</span></span
			>
		</div>
		<div class="info-row">
			<IconDimensions class="icon" />
			<!-- <span class="label">{{ $l.size }}:</span> -->
			<span class="value"
				>{{
					props.eventStore.sizeForEvent(props.selectedEvent).toFixed(2)
				}}km²</span
			>
		</div>
		<div class="info-row">
			<IconTemperature class="icon" />
			<!-- <span class="label">{{ $l.intensity }}:</span> -->
			<span class="value"
				>+{{
					props.eventStore.intensityForEvent(props.selectedEvent).toFixed(2)
				}}°C</span
			>
		</div>
		<div class="info-row">
			<div class="download-link" @click="downloadEvent" role="button">
				<IconDownload class="icon" />
			</div>
		</div>
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
	flex-direction: row;
	gap: 0.125rem 1rem;
	padding: 0 0.25rem;
	font-size: 0.75rem;
	justify-content: space-around;
}

.info-row {
	display: flex;
	align-items: center;
	gap: 0.25rem;
}

.icon {
	color: var(--text-primary);
	width: 1rem;
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
