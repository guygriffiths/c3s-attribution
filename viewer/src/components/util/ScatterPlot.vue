<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import scssVars from '@/assets/styles/scssVars.module.scss'
import * as d3 from 'd3'
import { IconZoomReset } from '@tabler/icons-vue'
import ChartDownloadMenu from '@/components/util/ChartDownloadMenu.vue'
import {
	createExportCanvas,
	plotRect,
	drawTitle,
	drawLinearAxes,
	downloadCanvas,
} from '@/lib/chart-export'

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
	lockX?: boolean
	title?: string
	xLabel?: string
	yLabel?: string
	xIsTime?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
	pointClick: [id: string]
}>()

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

// interactive pan/zoom transform (pixel space); identity = prop-driven auto view
const transform = ref<d3.ZoomTransform>(d3.zoomIdentity)
const isZoomed = computed(
	() =>
		transform.value.k !== 1 ||
		transform.value.x !== 0 ||
		transform.value.y !== 0,
)
// effective scales apply the current zoom/pan on top of the base scales
function effectiveScales() {
	return {
		xs: props.lockX
			? xScale.value
			: transform.value.rescaleX(xScale.value),
		ys: transform.value.rescaleY(yScale.value),
	}
}

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
	const { xs, ys } = effectiveScales()

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

		const cx = xs(st.x)
		const cy = ys(st.y)

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
			const cx = xs(st.x)
			const cy = ys(st.y)
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
		const cx = xs(st.x)
		const cy = ys(st.y)
		ctx.moveTo(cx + 6, cy)
		ctx.arc(cx, cy, 6, 0, 2 * Math.PI)
	}
	ctx.fill()

	// Selected
	if (props.selectedX !== null && props.selectedY !== null) {
		const cx = xs(props.selectedX)
		const cy = ys(props.selectedY)
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

// pan/zoom + click-to-select wiring
let zoomBehavior: d3.ZoomBehavior<HTMLCanvasElement, unknown> | null = null
let downPt: [number, number] | null = null

function nearestPointId(px: number, py: number): string | null {
	const { xs, ys } = effectiveScales()
	let bestId: string | null = null
	let bestD2 = 100 // ~10px hit radius (squared)
	for (const st of pointStates.values()) {
		if (!st.id || st.opacity <= 0) continue
		const cx = xs(st.x)
		const cy = ys(st.y)
		const d2 = (cx - px) ** 2 + (cy - py) ** 2
		if (d2 <= bestD2) {
			bestD2 = d2
			bestId = st.id
		}
	}
	return bestId
}

function onPointerDown(e: PointerEvent) {
	downPt = [e.offsetX, e.offsetY]
}
function onCanvasClick(e: MouseEvent) {
	if (downPt) {
		const dx = e.offsetX - downPt[0]
		const dy = e.offsetY - downPt[1]
		downPt = null
		if (dx * dx + dy * dy > 16) return // moved > ~4px => treat as pan, not a click
	}
	const id = nearestPointId(e.offsetX, e.offsetY)
	if (id) emit('pointClick', id)
}

function resetZoom() {
	if (!canvasRef.value || !zoomBehavior) return
	d3.select(canvasRef.value)
		.transition()
		.duration(200)
		.call(zoomBehavior.transform, d3.zoomIdentity)
}

onMounted(() => {
	if (!canvasRef.value) return
	zoomBehavior = d3
		.zoom<HTMLCanvasElement, unknown>()
		.scaleExtent([1, 40])
		// Trackpad pinch fires wheel events with ctrlKey set, so it zooms.
		// Plain wheel (two-finger scroll) passes through to the panel scroller.
		.filter((event) => {
			if (event.type === 'wheel') return event.ctrlKey || event.metaKey
			return !event.button
		})
		.on('zoom', (event) => {
			transform.value = event.transform
			needsRedraw.value = true
		})
	const sel = d3.select(canvasRef.value)
	sel.call(zoomBehavior)
	sel.on('dblclick.zoom', null) // leave double-click free for future use
	canvasRef.value.addEventListener('pointerdown', onPointerDown)
	canvasRef.value.addEventListener('click', onCanvasClick)
})

onBeforeUnmount(() => {
	if (canvasRef.value) {
		canvasRef.value.removeEventListener('pointerdown', onPointerDown)
		canvasRef.value.removeEventListener('click', onCanvasClick)
	}
})

// Re-baseline any manual zoom whenever the auto view (prop domain) changes,
// so the mode toggles act as an implicit reset.
watch(
	[() => props.xmin, () => props.xmax, () => props.ymin, () => props.ymax],
	() => {
		if (canvasRef.value && zoomBehavior && isZoomed.value) {
			d3.select(canvasRef.value).call(zoomBehavior.transform, d3.zoomIdentity)
		}
	},
)

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

function downloadCSV() {
	const headers = ['id', 'x', 'y', 'type']
	const allPoints = [
		...xyData.value.map((p) => [p.id ?? '', p.x, p.y, p.type]),
		...bgData.value.map((p) => [p.id ?? '', p.x, p.y, p.type]),
	]
	const csv = [headers, ...allPoints].map((r) => r.join(',')).join('\n')
	const blob = new Blob([csv], { type: 'text/csv' })
	const url = URL.createObjectURL(blob)
	const a = document.createElement('a')
	a.href = url
	a.download = (props.title ?? 'scatter') + '.csv'
	a.click()
	URL.revokeObjectURL(url)
}

function downloadImage() {
	// Freshly render the current view (respecting zoom/pan) to a clean PNG.
	const { xs, ys } = effectiveScales()
	const xDomain = xs.domain() as [number, number]
	const yDomain = ys.domain() as [number, number]
	const { canvas, ctx, width: cw, height: ch } = createExportCanvas()
	const plot = plotRect(cw, ch)
	const xSpan = xDomain[1] - xDomain[0] || 1
	const ySpan = yDomain[1] - yDomain[0] || 1
	const sx = (v: number) => plot.x + ((v - xDomain[0]) / xSpan) * plot.w
	const sy = (v: number) =>
		plot.y + plot.h - ((v - yDomain[0]) / ySpan) * plot.h

	drawTitle(ctx, props.title ?? '', cw)
	drawLinearAxes(ctx, {
		plot,
		xDomain,
		yDomain,
		xScale: sx,
		yScale: sy,
		xLabel: props.xLabel,
		yLabel: props.yLabel,
		xFormat: props.xIsTime
			? (v: number) => new Date(v).toISOString().slice(0, 10)
			: undefined,
	})

	const colorFor = (type: EventType | 'bg') =>
		type === 'hot'
			? scssVars.c3sred
			: type === 'cold'
				? scssVars.c3sblue
				: type === 'wet'
					? scssVars.c3steal
					: scssVars.c3spurple

	ctx.save()
	ctx.beginPath()
	ctx.rect(plot.x, plot.y, plot.w, plot.h)
	ctx.clip()

	// background points (faint)
	ctx.globalAlpha = 0.18
	ctx.fillStyle = scssVars.c3spurple
	for (const p of bgData.value) {
		ctx.beginPath()
		ctx.arc(sx(p.x), sy(p.y), 2, 0, 2 * Math.PI)
		ctx.fill()
	}

	// main points
	ctx.globalAlpha = 0.85
	for (const p of xyData.value) {
		ctx.fillStyle = colorFor(p.type)
		ctx.beginPath()
		ctx.arc(sx(p.x), sy(p.y), 3.5, 0, 2 * Math.PI)
		ctx.fill()
	}
	ctx.restore()

	downloadCanvas(canvas, props.title ?? 'scatter')
}

defineExpose({ downloadCSV, resetZoom })
</script>

<template>
	<div ref="containerRef" class="scatter-root chart">
		<h1 class="chart-title" v-if="props.title">{{ props.title }}</h1>
		<ChartDownloadMenu @csv="downloadCSV" @image="downloadImage" />
		<button
			v-if="isZoomed"
			class="reset-btn"
			@click="resetZoom"
			v-tooltip="'Reset zoom'"
			aria-label="Reset zoom"
		>
			<IconZoomReset :size="14" />
		</button>
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

	.reset-btn {
		position: absolute;
		top: 0px;
		right: 0px;
		z-index: 10;
		background: var(--panel-bg-night);
		border: 1px solid var(--divider);
		border-radius: 0;
		border-bottom-left-radius: 4px;
		padding: 2px 4px;
		cursor: pointer;
		opacity: 0.6;
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		transition: opacity 0.15s;
		&:hover {
			opacity: 1;
		}
		svg {
			position: static;
			opacity: 1;
			pointer-events: none;
			width: 14px;
			height: 14px;
			color: inherit;
		}
	}

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
		touch-action: none;
		cursor: crosshair;
	}
}
</style>
