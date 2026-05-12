<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import scssVars from '@/assets/styles/scssVars.module.scss'
import * as d3 from 'd3'

type Props = {
	xdata: number[]
	xmin: number
	xmax: number
	ydata: number[]
	ymin: number
	ymax: number
	xbg?: number[]
	ybg?: number[]
	types?: (EventType | 'bg')[]
	ids?: string[]
	selectedX: number | null
	selectedY: number | null
	hoverId?: string | null
	xscale?: number
	yscale?: number
	title?: string
}

const props = defineProps<Props>()

// container + canvas refs
const containerRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const width = ref(0)
const height = ref(0)
const resizeObserver = ref<ResizeObserver | null>(null)

onMounted(() => {
	if (!containerRef.value) return
	let resizeTimeout: ReturnType<typeof setTimeout> | null = null
	resizeObserver.value = new ResizeObserver((entries) => {
		for (const entry of entries) {
			if (entry.contentRect) {
				// This works nicely with resizing.
				if (resizeTimeout) {
					clearTimeout(resizeTimeout)
				}
				resizeTimeout = setTimeout(() => {
					width.value = Math.floor(entry.contentRect.width)
					height.value = Math.floor(entry.contentRect.height)
				}, 0)
			}
		}
	})
	resizeObserver.value.observe(containerRef.value)
})
onBeforeUnmount(() => {
	if (resizeObserver.value && containerRef.value)
		resizeObserver.value.unobserve(containerRef.value)
	resizeObserver.value = null
})

// domains + scales
const xDataExtent = computed(() => {
	const dd = props.xdata ?? []
	return dd.length ? (d3.extent(dd) as [number, number]) : [0, 1]
})
const yDataExtent = computed(() => {
	const dd = props.ydata ?? []
	return dd.length ? (d3.extent(dd) as [number, number]) : [0, 1]
})

const x0 = computed(() => props.xmin ?? xDataExtent.value[0])
const x1 = computed(() => props.xmax ?? xDataExtent.value[1])
const y0 = computed(() => props.ymin ?? yDataExtent.value[0])
const y1 = computed(() => props.ymax ?? yDataExtent.value[1])

function expandDomain([a, b]: [number, number]): [number, number] {
	if (a === b) {
		const delta = Math.abs(a) * 0.01 || 1
		return [a - delta, b + delta]
	}
	return [a, b]
}
const xDomain = computed(() => expandDomain([x0.value, x1.value]))
const yDomain = computed(() => expandDomain([y0.value, y1.value]))

const padding = 4
const xScale = computed(() =>
	d3
		.scaleLinear()
		.domain(xDomain.value)
		.range([padding, width.value - padding]),
)
const yScale = computed(() =>
	d3
		.scaleLinear()
		.domain(yDomain.value)
		.range([height.value - padding, padding]),
)

// point list
const xyData = computed(() => {
	const xd = props.xdata ?? []
	const yd = props.ydata ?? []
	const n = Math.min(xd.length, yd.length)
	const pts: {
		x: number
		y: number
		type: EventType | 'bg'
		id: string | null
	}[] = []
	for (let i = 0; i < n; i++) {
		pts.push({
			x: xd[i],
			y: yd[i],
			type: props.types
				? i < props.types.length
					? props.types[i]
					: 'hot'
				: 'hot',
			id: props.ids ? (i < props.ids.length ? props.ids[i] : null) : null,
		})
	}
	return pts
})
const bgData = computed(() => {
	if (!props.xbg || !props.ybg) return []
	const xd = props.xbg
	const yd = props.ybg
	const n = Math.min(xd.length, yd.length)
	const pts: {
		x: number
		y: number
		type: 'hot' | 'cold' | 'bg'
		id: string | null
	}[] = []
	for (let i = 0; i < n; i++) {
		pts.push({
			x: xd[i],
			y: yd[i],
			type: 'bg',
			id: null,
		})
	}
	return pts
})

interface PointState {
	opacity: number
	target: number
	lastUpdate: number
	x: number
	y: number
	id: string | null
	color: string
}

// fade bookkeeping
const pointStates = new Map<string, PointState>()
const bgPointStates = new Map<string, PointState>()
const fadeDuration = 50 // ms

const computeOpacity = (n: number, maxOpacity = 0.8) =>
	Math.min(maxOpacity, maxOpacity * Math.pow(n, -0.2))

// dirty redraw
const needsRedraw = ref(true)
watch(
	[
		() => props.xdata,
		() => props.ydata,
		() => props.xbg,
		() => props.ybg,
		() => props.types,
		() => props.ids,
		width,
		height,
		xScale,
		yScale,
		() => props.hoverId,
		() => props.selectedX,
		() => props.selectedY,
	],
	() => {
		// TODO Split into two - one for data changes, one for size changes. The size one can then use the progress indicator to do a smooth move of all the points.
		// Add update x/y to updatePointOpacity? Then calculate the scaled points in the updateMethod
		needsRedraw.value = true
	},
)

watch(
	() => xyData.value,
	(newPts) => {
		const now = performance.now()
		const newIds = new Set(newPts.map((p) => p.id ?? `__idx_${p.x}_${p.y}`))
		const fullOpacity = computeOpacity(xyData.value.length)

		// Track nearest points if we have a selection
		let nearestPoints: Array<{ key: string; distance: number }> = []
		const selectedX = props.selectedX
		const selectedY = props.selectedY
		const hasSelection = selectedX !== null && selectedY !== null

		// mark new + update existing
		for (const p of newPts) {
			const key = p.id ?? `__idx_${p.x}_${p.y}`
			if (!pointStates.has(key)) {
				pointStates.set(key, {
					opacity: 0,
					target: fullOpacity,
					lastUpdate: now,
					x: p.x,
					y: p.y,
					id: p.id,
					color:
						p.type === 'hot'
							? scssVars.c3sred
							: p.type === 'cold'
								? scssVars.c3sblue
								: p.type === 'wet'
									? scssVars.c3steal
									: scssVars.c3spurple,
				})
			} else {
				const st = pointStates.get(key)!
				st.target = fullOpacity
				st.lastUpdate = now
				st.x = p.x
				st.y = p.y
			}

			// Calculate distance to selected point
			if (hasSelection && props.xscale && props.yscale) {
				const dx = p.x - selectedX
				const dy = p.y - selectedY
				const distance = dx * dx + dy * dy // squared distance is fine for comparison
				nearestPoints.push({ key, distance })
			}
		}
		// mark new + update existing
		for (const p of bgData.value) {
			const key = p.id ?? `__idx_${p.x}_${p.y}`
			if (!bgPointStates.has(key)) {
				bgPointStates.set(key, {
					opacity: 0,
					target: 0,
					lastUpdate: now,
					x: p.x,
					y: p.y,
					id: p.id,
					color: scssVars.c3spurple,
				})
			} else {
				const st = bgPointStates.get(key)!
				st.target = 0.1 * fullOpacity
				st.lastUpdate = now
				st.x = p.x
				st.y = p.y
			}
		}
		// console.log('bg points', bgPointStates.size)
		// Keep only the N nearest (adjust N as needed)
		// if (hasSelection && nearestPoints.length > 0) {
		// 	const N = 10 // or make this a prop
		// 	nearestPoints.sort((a, b) => a.distance - b.distance)
		// 	const nearestKeys = new Set(nearestPoints.slice(0, N).map((p) => p.key))

		// 	// Highlight nearest points (example: boost opacity or change color)
		// 	for (const key of pointStates.keys()) {
		// 		const st = pointStates.get(key)!
		// 		if (nearestKeys.has(key)) {
		// 			st.target = 1.0 // full opacity for nearest
		// 			st.color = scssVars.highlight // or add a highlight color
		// 		}
		// 	}
		// }

		// mark removed
		for (const key of pointStates.keys()) {
			if (!newIds.has(key)) {
				const st = pointStates.get(key)!
				st.target = 0
				st.lastUpdate = now
			}
		}
	},
)

function draw() {
	if (!canvasRef.value) return
	const now = performance.now()
	let anyAnimating = false
	const ctx = canvasRef.value.getContext('2d')!
	ctx.clearRect(0, 0, width.value, height.value)
	const highlights = [] as PointState[]

	ctx.globalCompositeOperation = 'source-over'
	ctx.globalAlpha = 0.01
	ctx.beginPath()

	for (const st of bgPointStates.values()) {
		const elapsed = now - st.lastUpdate
		const progress = Math.min(1, elapsed / fadeDuration)
		st.opacity += (st.target - st.opacity) * progress
		st.lastUpdate = now

		if (Math.abs(st.opacity - st.target) > 0.01) {
			anyAnimating = true
			needsRedraw.value = true
		} else {
			st.opacity = st.target
		}

		if (st.opacity <= 0) continue

		const cx = xScale.value(st.x)
		const cy = yScale.value(st.y)

		ctx.fillStyle = st.color
		ctx.globalAlpha = st.opacity

		ctx.moveTo(cx + 2, cy) // breaks the path so arcs dinnae join
		ctx.arc(cx, cy, 2, 0, 2 * Math.PI)
	}

	ctx.fill()
	ctx.globalCompositeOperation = 'multiply'
	for (const st of pointStates.values()) {
		// ease opacity toward target
		const elapsed = now - st.lastUpdate
		const progress = Math.min(1, elapsed / fadeDuration)
		st.opacity += (st.target - st.opacity) * progress
		st.lastUpdate = now
		if (Math.abs(st.opacity - st.target) > 0.01) {
			anyAnimating = true
			needsRedraw.value = true
		} else {
			st.opacity = st.target
		}

		if (st.opacity <= 0) continue

		if (st.id === props.hoverId) {
			highlights.push(st)
		} else {
			const cx = xScale.value(st.x)
			const cy = yScale.value(st.y)
			ctx.globalAlpha = st.opacity
			ctx.beginPath()
			ctx.arc(cx, cy, 3, 0, 2 * Math.PI)
			ctx.fillStyle = st.color
			ctx.fill()
		}
	}

	// Highlights
	ctx.globalCompositeOperation = 'source-over'
	ctx.globalAlpha = 1
	ctx.fillStyle = scssVars.lightbulb
	ctx.beginPath()
	for (const st of highlights) {
		const cx = xScale.value(st.x)
		const cy = yScale.value(st.y)
		ctx.moveTo(cx + 6, cy)
		ctx.arc(cx, cy, 6, 0, 2 * Math.PI)
	}
	ctx.fill()

	// Selected
	if (props.selectedX !== null && props.selectedY !== null) {
		const cx = xScale.value(props.selectedX)
		const cy = yScale.value(props.selectedY)
		ctx.beginPath()
		ctx.arc(cx, cy, 6, 0, 2 * Math.PI)
		ctx.fill()
	}

	// Prune
	for (const [key, st] of pointStates) {
		if (st.target === 0 && st.opacity <= 0.01) pointStates.delete(key)
	}

	return anyAnimating
}

function loop() {
	requestAnimationFrame(loop)
	// console.log('loop tick')
	if (needsRedraw.value) {
		const stillAnimating = draw()
		if (!stillAnimating) {
			needsRedraw.value = false
		}
	}
}
onMounted(() => loop())
</script>

<template>
	<div ref="containerRef" class="scatter-root chart">
		<h1 class="chart-title" v-if="props.title">{{ props.title }}</h1>
		<canvas
			ref="canvasRef"
			class="scatter-canvas"
			:width="width"
			:height="height"
		/>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.scatter-root {
	width: 100%;
	height: 100%;
	position: relative;

	.tabler-icon {
		width: min(35%, 2.5rem);
		height: auto;
		color: white;
		opacity: 0.8;
		position: absolute;
		pointer-events: none;
		user-select: none;
		z-index: 10;
	}

	.xicon {
		bottom: 4px;
		right: 4px;
	}

	.yicon {
		top: 4px;
		left: 0px;
	}

	.scatter-canvas {
		width: 100%;
		height: 100%;
		position: absolute;
		top: 0;
		left: 0;
		z-index: 0;
		border-radius: 0;
	}
}
</style>
