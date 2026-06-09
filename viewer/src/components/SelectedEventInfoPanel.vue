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
	IconTemperatureMinus,
	IconTemperaturePlus,
	IconCloudRain,
} from '@tabler/icons-vue'
import { niceNumber } from '@/lib/utils'

const props = defineProps<{
	selectedEvent: ExtremeEvent | ExtremeEventFull
	eventStore: any
}>()

const $l = useLabels()

// Format helpers
const timeRange = computed(() => {
	if (!props.selectedEvent?.times?.length) return '—'
	const start = new Date(props.selectedEvent.times[0])
	const end = new Date(props.selectedEvent.times.at(-1) || start)
	if (start.getMonth() === end.getMonth()) {
		return `${format(start, 'do')} → ${format(end, 'do MMM yyyy')}`
	}
	return `${format(start, 'do MMM')} → ${format(end, 'do MMM yyyy')}`
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
		<h3 class="panel-title">{{ $l.eventInformation }}</h3>
		<button
			class="download-button glassy color"
			@click="downloadEvent"
			v-tooltip="$l.downloadEventData"
		>
			<IconDownload class="icon" aria-hidden="true" />
		</button>
		<div class="info-row header">
			<IconTemperatureSun
				v-if="props.selectedEvent.event_type === 'hot'"
				class="icon"
				aria-hidden="true"
			/>
			<IconTemperatureSnow
				v-else-if="props.selectedEvent.event_type === 'cold'"
				class="icon"
				aria-hidden="true"
			/>
			<IconCloudRain v-else class="icon" aria-hidden="true" />
			<h2 class="label mono">{{ timeRange }}</h2>
		</div>
		<div class="info-row" v-tooltip="$l.duration">
			<IconStopwatch class="icon" aria-hidden="true" />
			<!-- <span class="label">{{ $l.duration }}:</span> -->
			<span class="value mono"
				>{{ eventStore.durationForEvent(props.selectedEvent) }}
				{{ eventStore.durationUnits }}
			</span>
		</div>
		<div class="info-row" v-tooltip="$l.size">
			<IconDimensions class="icon" aria-hidden="true" />
			<!-- <span class="label">{{ $l.size }}:</span> -->
			<span class="value mono"
				>{{ niceNumber(eventStore.sizeForEvent(props.selectedEvent)) }}
				{{ eventStore.sizeUnits }}</span
			>
		</div>
		<div
			class="info-row"
			v-tooltip="
				props.selectedEvent.event_type === 'hot' ? $l.maxTemp : props.selectedEvent.event_type === 'cold' ? $l.minTemp : $l.wetIntensityLabel
			"
		>
			<IconTemperaturePlus
				v-if="props.selectedEvent.event_type === 'hot'"
				class="icon"
				aria-hidden="true"
			/>
			<IconTemperatureMinus
				v-else-if="props.selectedEvent.event_type === 'cold'"
				class="icon"
				aria-hidden="true"
			/>
			<IconCloudRain class="icon" v-else aria-hidden="true" />
			<!-- <span class="label">{{ $l.intensity }}:</span> -->
			<span class="value mono"
				>{{ niceNumber(eventStore.intensityForEvent(props.selectedEvent)) }}
				{{ selectedEvent.event_type === 'hot'
					? eventStore.heatIntensityUnits
					: selectedEvent.event_type === 'cold'
						? eventStore.coldIntensityUnits
						: eventStore.wetIntensityUnits
				}}
			</span>
		</div>

		<div class="info-row" v-tooltip="$l.reportId">
			<IconReport class="icon" aria-hidden="true" /><span class="value mono"
				>N/A</span
			>
		</div>
		<slot></slot>
	</div>
</template>

<style scoped>
.event-info {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	align-items: flex-start;
	gap: 0.125rem 1.25rem;
	padding: 0rem 1rem 1rem;
	font-size: 0.75rem;
	justify-content: space-between;
	position: relative;
	z-index: 0;

	.panel-title {
		align-self: flex-end;
		margin-right: 0;
		margin-left: 1rem;
	}
}

.download-button {
	position: absolute;
	top: 0;
	left: 0;
	padding: 0.25rem 0 0.25rem 0.25rem;
	border-bottom-left-radius: 0;
	border-top-right-radius: 0;
	display: flex;
	justify-content: center;
	align-items: center;
	z-index: 10;
	box-shadow: none !important;
	width: 1.6rem;
	height: 1.6rem;

	.icon {
		width: 1.4rem;
		height: 1.4rem;
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
		margin-left: 0.5rem;
		.label {
			/* margin-bottom: 0.5rem; */
			font-size: 1rem;
			font-weight: bold;
			display: flex;
			align-items: center;
			justify-content: flex-end;
			text-wrap: wrap;
			flex-shrink: 1;
			margin-top: 0;
			margin-bottom: 0;
			text-align: center;
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
