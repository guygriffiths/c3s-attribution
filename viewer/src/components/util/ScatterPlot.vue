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
	types?: ('hot' | 'cold')[]
	ids?: string[]
	highlightId?: string | null
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
	resizeObserver.value = new ResizeObserver((entries) => {
		for (const entry of entries) {
			if (entry.contentRect) {
				width.value = Math.floor(entry.contentRect.width)
				height.value = Math.floor(entry.contentRect.height)
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
		type: 'hot' | 'cold'
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

// fade bookkeeping
const pointStates = new Map<
	string,
	{
		opacity: number
		target: number
		lastUpdate: number
		x: number
		y: number
		id: string | null
		type: 'hot' | 'cold'
	}
>()
const fadeDuration = 50 // ms

const computeOpacity = (n: number, maxOpacity = 0.5) =>
	Math.min(maxOpacity,  maxOpacity * Math.pow(n, -0.33))

watch(xyData, (newPts) => {
	const now = performance.now()
	const newIds = new Set(newPts.map((p) => p.id ?? `__idx_${p.x}_${p.y}`))

	const fullOpacity = computeOpacity(xyData.value.length)
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
				type: p.type,
			})
		} else {
			const st = pointStates.get(key)!
			st.target = fullOpacity
			st.lastUpdate = now
		}
	}

	// mark removed -> fade out
	for (const [key, st] of pointStates) {
		if (!newIds.has(key)) {
			st.target = 0
			st.lastUpdate = now
		}
	}
})

// dirty redraw
const needsRedraw = ref(true)
watch([xyData, width, height, () => props.highlightId], () => {
	needsRedraw.value = true
})

function draw() {
	if (!canvasRef.value) return
	const ctx = canvasRef.value.getContext('2d')!
	ctx.clearRect(0, 0, width.value, height.value)

	const now = performance.now()
	let anyAnimating = false

	const highlights = []
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

		ctx.globalCompositeOperation = 'multiply'
		if (st.id === props.highlightId) {
			highlights.push(st)
		} else {
			const cx = xScale.value(st.x)
			const cy = yScale.value(st.y)
			ctx.globalAlpha = st.opacity
			ctx.beginPath()
			ctx.arc(cx, cy, 4, 0, 2 * Math.PI)
			ctx.fillStyle = st.type === 'hot' ? scssVars.c3sred : scssVars.c3sblue
			ctx.strokeStyle = st.type === 'hot' ? scssVars.c3sred : scssVars.c3sblue
			ctx.fill()
			ctx.stroke()
		}
	}
	for (const st of highlights) {
		const cx = xScale.value(st.x)
		const cy = yScale.value(st.y)
		ctx.globalAlpha = 1
		ctx.beginPath()
		ctx.arc(cx, cy, 6, 0, 2 * Math.PI)
		ctx.fillStyle = scssVars.lightbulb
		ctx.strokeStyle = scssVars.lightbulb
		ctx.fill()
		ctx.stroke()
	}
	ctx.globalAlpha = 1.0

	// prune fully invisible
	for (const [key, st] of pointStates) {
		if (st.target === 0 && st.opacity <= 0.01) pointStates.delete(key)
	}

	if (anyAnimating) needsRedraw.value = true
	else needsRedraw.value = false
}

function loop() {
	requestAnimationFrame(loop)
	if (needsRedraw.value) draw()
}
onMounted(() => loop())
</script>

<template>
	<div ref="containerRef" class="scatter-root">
		<canvas
			ref="canvasRef"
			class="scatter-canvas"
			:width="width"
			:height="height"
		/>
	</div>
</template>

<style scoped lang="scss">
.scatter-root {
	width: 100%;
	height: 100%;
}
.scatter-canvas {
	width: 100%;
	height: 100%;
	display: block;
	border: 1px solid #e2e8f0;
}
</style>
