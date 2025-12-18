<script setup lang="ts">
import {
	IconChartAreaLine,
	IconLayersIntersect,
	IconCalendarTime,
	IconStack3,
	IconStopwatch,
} from '@tabler/icons-vue'
import { useLabels } from '@/lib/labels'

const $l = useLabels()

const mode = defineModel<ViewMode>({ required: true })
</script>

<template>
	<div class="mode-toggle-root">
		<button
			class="mode-button glassy"
			:class="{ [mode]: true, selected: mode === 'timemachine' }"
			@click="mode = 'timemachine'"
			:aria-pressed="mode === 'timemachine'"
			v-tooltip="$l.selectTimeMachineMode"
			role="switch"
		>
			<IconCalendarTime
				class="icon timeline-icon"
				:class="{ active: mode === 'timemachine' }"
				size="32"
				aria-hidden="true"
			/>
		</button>
		<button
			class="mode-button glassy"
			:class="{ [mode]: true, selected: mode === 'heatmap' }"
			@click="mode = 'heatmap'"
			:aria-pressed="mode === 'heatmap'"
			v-tooltip="$l.selectHeatmapMode"
			role="switch"
		>
			<IconLayersIntersect
				class="icon heatmap-icon"
				:class="{ active: mode === 'heatmap' }"
				size="32"
				aria-hidden="true"
			/>
		</button>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';



.mode-button {
	// Reset button styles
	border: none;
	padding: 0;
	cursor: pointer;

	width: $modeButtonWidth;
	height: $modeButtonHeight;

	border-radius: 0;
	padding: 1.5rem 1rem 0.25rem 1rem;

	&:first-child {
		border-bottom-left-radius: $borderRadius;
	}

	&:last-child {
		border-bottom-right-radius: $borderRadius;
	}
}
</style>
