<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLabels } from '@/lib/labels'
import { format } from 'date-fns'
import {
	IconStopwatch,
	IconDimensions,
	IconDownload,
	IconReport,
	IconTemperature,
	IconTemperatureSun,
	IconTemperatureSnow,
} from '@tabler/icons-vue'
import { dayStr } from '@/lib/time-utils'

const props = defineProps<{
	selectedEvent: ExtremeEvent
	eventStore: any
}>()

const $l = useLabels()

// Format helpers
const timeRange = computed(() => {
	if (!props.selectedEvent?.times?.length) return '—'
	const start = new Date(props.selectedEvent.times[0])
	const end = new Date(props.selectedEvent.times.at(-1) || start)
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
	<div class="event-info panel">
		<button class="download-button glassy color" @click="downloadEvent">
			<IconDownload class="icon" />
		</button>
		<div class="info-row header">
			<IconTemperatureSun
				v-if="props.selectedEvent.event_type === 'hot'"
				class="icon"
			/>
			<IconTemperatureSnow
				v-else-if="props.selectedEvent.event_type === 'cold'"
				class="icon"
			/>
			<IconTemperature class="icon" v-else />
			<h2 class="mono">{{ timeRange }}</h2>
		</div>
		<div class="info-row">
			<IconStopwatch class="icon" />
			<!-- <span class="label">{{ $l.duration }}:</span> -->
			<span class="value mono"
				>{{ eventStore.durationForEvent(props.selectedEvent) }} days
			</span>
		</div>
		<div class="info-row">
			<IconDimensions class="icon" />
			<!-- <span class="label">{{ $l.size }}:</span> -->
			<span class="value mono"
				>{{ eventStore.sizeForEvent(props.selectedEvent).toFixed(2) }}km²</span
			>
		</div>
		<div class="info-row">
			<IconTemperature class="icon" />
			<!-- <span class="label">{{ $l.intensity }}:</span> -->
			<span class="value mono"
				>+{{
					eventStore.intensityForEvent(props.selectedEvent).toFixed(2)
				}}°C</span
			>
		</div>

		<div class="info-row">
			<IconReport class="icon" /><span class="value mono">N/A</span>
		</div>
		<slot></slot>
	</div>
</template>

<style scoped>
.event-info {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	align-items: center;
	gap: 0.125rem 1.25rem;
	padding: 0.5rem 1rem;
	font-size: 0.75rem;
	justify-content: space-between;
	position: relative;
	z-index: 0;
}

.download-button {
	position: absolute;
	top: 0;
	left: 0;
	padding: 0.25rem 0 0.25rem 0.25rem;
	border-top-right-radius: 0;
	border-bottom-left-radius: 0;
	display: flex;
	justify-content: center;
	align-items: center;
	z-index: 10;
	box-shadow: none !important;

	.icon {
		width: 1.5rem;
		height: 1.5rem;
		color: var(--text-on-primary);
	}
}

.info-row {
	display: flex;
	gap: 0.25rem;
	justify-content: flex-start;
	align-items: center;
	overflow: hidden;
	z-index: 5;

	&.header,
	&.title {
		flex-shrink: 0;
		flex-basis: auto;
		display: flex;
		justify-content: center;
		padding: 0.25rem;
		width: 100%;
		.tabler-icon {
			width: 2rem;
		}
	}

	&.header {
		position: relative;
		z-index: 10;
		.label {
			/* margin-bottom: 0.5rem; */
			font-size: 1.2rem;
			font-weight: bold;
			display: flex;
			align-items: center;
			/* position: absolute;
			left: 50%;
			transform: translateX(-50%); */
		}
	}
}

.download-link {
	display: flex;
	align-items: center;
}

.icon {
	color: var(--text-primary);
	width: 1.25rem;
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
	font-size: 1rem;
}
</style>
