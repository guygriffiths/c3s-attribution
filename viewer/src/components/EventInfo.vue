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
  if(start.getMonth() === end.getMonth()) {
    return `${format(start, 'dd')} → ${format(end, 'dd MMM')}`
  }
  return `${format(start, 'dd MMM')} → ${format(end, 'dd MMM')}`
	// return `${start.toLocaleDateString()} → ${end.toLocaleDateString()}`
})

const mean = computed(() => props.selectedEvent?.mean_value?.toFixed(2) ?? '—')
const peak = computed(() => props.selectedEvent?.peak_value?.toFixed(2) ?? '—')
const area = computed(
	() => props.selectedEvent?.total_area?.toFixed(1) + ' km²' ?? '—',
)
</script>

<template>
	<div class="event-info-panel">
		<!-- <div class="info-row">
      <FontAwesomeIcon :icon="faClock" class="icon" />
      <span class="label">Debug:</span>
      <span class="value">{{ props.selectedEvent }}</span>
    </div> -->
		<div class="info-row">
			<FontAwesomeIcon :icon="faClock" class="icon" />
			<span class="label">{{ $l.duration }}:</span>
			<span class="value"
				>{{ props.eventStore.durationForEvent(props.selectedEvent)
				}} days <span class="small">({{ timeRange }})</span></span
			>
		</div>
		<div class="info-row">
			<FontAwesomeIcon :icon="faExpand" class="icon" />
			<span class="label">{{ $l.size }}:</span>
			<span class="value">{{ props.eventStore.sizeForEvent(props.selectedEvent).toFixed(2) }}km²</span>
		</div>
		<div class="info-row">
			<FontAwesomeIcon :icon="faTemperatureHigh" class="icon" />
			<span class="label">{{ $l.intensity }}:</span>
			<span class="value">{{ props.eventStore.intensityForEvent(props.selectedEvent).toFixed(2) }}°C</span>
		</div>
		<div class="info-row">
			<a :href="props.eventStore.downloadLinkForEvent(props.selectedEvent)" :download="`event_${props.selectedEvent?.id || 'data'}.json`">
			<FontAwesomeIcon :icon="faDownload" class="icon" /></a>
			<span class="label">{{ $l.download }} </span>
		</div>
	</div>
</template>

<style scoped>
.event-info-panel {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	gap: 0.125rem 2rem;
	padding: 0 0.25rem;
	background: #f9f9f9;
	border-radius: 0.75rem;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	font-size: 0.75rem;
	justify-content: space-around;
}

.info-row {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.icon {
	color: #444;
	width: 1rem;
}

.label {
	font-weight: 600;
	flex-shrink: 0;
	/* min-width: 3.5rem; */
}

.value {
	flex-grow: 1;
	text-align: left;

  .small {
    font-size: 0.65rem;
    color: #666;
    margin-left: 0.25rem;
  }
}
</style>
