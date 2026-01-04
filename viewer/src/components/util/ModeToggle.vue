<script setup lang="ts">
import { IconCalendarTime, IconEyePin } from '@tabler/icons-vue'
import { useLabels } from '@/lib/labels'
import { onMounted, ref } from 'vue'

const $l = useLabels()

const mode = defineModel<ViewMode>({ required: true })

const eyecon = ref<SVGElement | null>(null)
const timeMachineIcon = ref<SVGElement | null>(null)
onMounted(() => {
	const pupilElement = eyecon.value?.querySelector('path:first-child')
	pupilElement?.setAttribute('transition', `transform 0.5s ease;`)
	// const handsElement = timeMachineIcon.value?.querySelector('path:last-child')
	window.addEventListener('mousemove', (e: MouseEvent) => {
		if (pupilElement) {
			if (mode.value === 'heatmap') {
				const rect = pupilElement.getBoundingClientRect()
				if (rect) {
					const eyeCenterX = rect.left + rect.width / 2
					const eyeCenterY = rect.top + rect.height / 2
					const deltaX = e.clientX - eyeCenterX
					const deltaY = e.clientY - eyeCenterY
					const angle = Math.atan2(deltaY, deltaX)
					const radius = Math.min(rect.width, rect.height) * 0.15
					const pupilX = Math.cos(angle) * radius
					const pupilY = Math.sin(angle) * radius
					pupilElement.setAttribute(
						'transform',
						`translate(${pupilX}, ${pupilY})`,
					)
				}
				// handsElement?.setAttribute('transform', `rotate(0)`)
			} else if (mode.value === 'timemachine') {
				pupilElement.setAttribute('transform', `translate(0, 0)`)
			}
		}
	})
})
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
				ref="timeMachineIcon"
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
			<IconEyePin
				ref="eyecon"
				class="icon heatmap-icon eye"
				:class="{ active: mode === 'heatmap' }"
				size="32"
				aria-hidden="true"
			/>
			<!-- <div class="overview-icon">
				<IconEye
					class="icon heatmap-icon eye"
					:class="{ active: mode === 'heatmap' }"
					size="32"
					aria-hidden="true"
				/>
				<IconMap
					class="icon heatmap-icon map"
					:class="{ active: mode === 'heatmap' }"
					size="32"
					aria-hidden="true"
				/>
			</div> -->
		</button>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

.overview-icon {
	position: relative;
	width: 32px;
	height: 32px;

	.heatmap-icon {
		position: absolute;
	}

	.eye {
		top: 0;
		left: 0;
	}

	.map {
		top: 50%;
		left: 0;
		transform: scaleY(0.5);
	}
}

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
