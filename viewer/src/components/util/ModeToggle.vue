<script setup lang="ts">
import {
	IconChartAreaLine,
	IconLayersIntersect,
	IconCalendarTime,
	IconStack3,
	IconStopwatch,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'
import { computed } from 'vue'

const mode = defineModel<ViewMode>({ required: true })
const store = useStore()

const ariaLabel = computed(() =>
	mode.value === 'heatmap'
		? 'Switch to timeline mode'
		: 'Switch to heatmap mode',
)
</script>

<template>
	<div class="mode-toggle-root">
		<button
			class="mode-button glassy"
			:class="{ [mode]: true, selected: mode === 'timemachine' }"
			@click="mode = 'timemachine'"
			:aria-label="ariaLabel"
			:aria-pressed="mode === 'timemachine'"
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
			aria-label="Select heatmap mode"
			:aria-pressed="mode === 'heatmap'"
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
