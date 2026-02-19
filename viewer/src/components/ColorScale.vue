<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

interface Props {
	colorfunc: (val: number) => string
    domain: [number, number] | number[]
}

const props = defineProps<Props>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const height = 20

// Format numbers nicely (remove unnecessary decimals)
const formatValue = (val: number): string => {
	if (Number.isInteger(val)) return val.toString()
	return val.toFixed(1)
}

// Draw gradient on canvas for smooth color transitions
const drawGradient = () => {
	if (!canvasRef.value || !containerRef.value) return
	
	const container = containerRef.value
	const canvas = canvasRef.value
	const ctx = canvas.getContext('2d')
	if (!ctx) return
	
	// Get available width from container
	const width = container.clientWidth
	
	// Update canvas size
	canvas.width = width
	canvas.height = height
	
	// Draw smooth gradient across canvas width
	for (let x = 0; x < width; x++) {
		const value = props.domain[0] + (x / width) * (props.domain[1] - props.domain[0])
		const color = props.colorfunc(value)
		
		ctx.fillStyle = color
		ctx.fillRect(x, 0, 1, height)
	}
}

// Set up resize observer
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
	drawGradient()
	
	// Watch for container size changes
	if (containerRef.value) {
		resizeObserver = new ResizeObserver(() => {
			drawGradient()
		})
		resizeObserver.observe(containerRef.value)
	}
})

onUnmounted(() => {
	if (resizeObserver) {
		resizeObserver.disconnect()
	}
})

watch(() => props.domain, () => {
    drawGradient()
})
</script>

<template>
	<div class="color-scale">
		<div class="scale-wrapper">
			<span class="value min">{{ formatValue(props.domain[0]) }}</span>
			
			<div class="scale-bar" ref="containerRef">
				<canvas
					ref="canvasRef"
					:height="height"
					class="gradient"
				/>
			</div>
			
			<span class="value max">{{ formatValue(props.domain[1]) }}</span>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.color-scale {
	display: flex;
	flex-direction: column;
	gap: 0.25rem;
	align-items: stretch;
	font-size: 0.875rem;
	width: 100%;
	
	.scale-label {
		font-weight: 500;
		opacity: 0.8;
	}
	
	.scale-wrapper {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
	}
	
	.value {
		font-size: 0.75rem;
		font-weight: 500;
		min-width: 2rem;
		text-align: center;
		opacity: 0.9;
		flex-shrink: 0;
		
		&.min {
			text-align: right;
		}
		
		&.max {
			text-align: left;
		}
	}
	
	.scale-bar {
		position: relative;
		border-radius: $borderRadius;
		overflow: hidden;
		box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2);
		flex: 1 1 auto;
		min-width: 0;
		
		.gradient {
			display: block;
			width: 100%;
			height: 20px;
			border-radius: $borderRadius;
		}
	}
	
	.unit {
		font-size: 0.75rem;
		opacity: 0.6;
		font-style: italic;
	}
}
</style>