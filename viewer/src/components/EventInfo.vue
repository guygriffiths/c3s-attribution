<script setup>
import { computed } from 'vue'
import { faClock, faSignal, faFire, faMap } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

const props = defineProps({
  selectedEvent: {
    type: Object,
    required: true
  }
})

// Format helpers
const timeRange = computed(() => {
  if (!props.selectedEvent?.times?.length) return '—'
  const start = new Date(props.selectedEvent.times[0])
  const end = new Date(props.selectedEvent.times.at(-1))
  return `${start.toLocaleDateString()} → ${end.toLocaleDateString()}`
})

const mean = computed(() => props.selectedEvent?.mean_value?.toFixed(2) ?? '—')
const peak = computed(() => props.selectedEvent?.peak_value?.toFixed(2) ?? '—')
const area = computed(() => props.selectedEvent?.total_area?.toFixed(1) + ' km²' ?? '—')
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
      <span class="label">Time:</span>
      <span class="value">{{ timeRange }}</span>
    </div>
    <div class="info-row">
      <FontAwesomeIcon :icon="faSignal" class="icon" />
      <span class="label">Mean:</span>
      <span class="value">{{ mean }}</span>
    </div>
    <div class="info-row">
      <FontAwesomeIcon :icon="faFire" class="icon" />
      <span class="label">Peak:</span>
      <span class="value">{{ peak }}</span>
    </div>
    <div class="info-row">
      <FontAwesomeIcon :icon="faMap" class="icon" />
      <span class="label">Area:</span>
      <span class="value">{{ area }}</span>
    </div>
  </div>
</template>

<style scoped>
.event-info-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #f9f9f9;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  font-size: 0.95rem;
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
  min-width: 3.5rem;
}

.value {
  flex-grow: 1;
  text-align: left;
}
</style>
