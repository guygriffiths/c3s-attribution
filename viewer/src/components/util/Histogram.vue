<script setup lang="ts">
/*
  Histogram.vue
  Props:
    - data: number[]                (required)
    - xmin?: number | null          (optional; if null -> computed from data)
    - xmax?: number | null          (optional; if null -> computed from data)
    - nbins: number                 (default 20)
    - yMaxPct?: number | null       (optional fixed Y% max; if null -> auto from data)
*/

import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as d3 from 'd3'
import { binGradient } from '@/lib/utils'
import scssVars from '@/assets/styles/scssVars.module.scss'
import { IconDimensions, IconHourglassHigh, IconTemperature } from '@tabler/icons-vue'

type Props = {
	data: number[]
	xmin: number
	xmax: number
	labelFunc?: (v: number) => string
	units?: string | null
	nbins?: number
	yMaxPct?: number | null
	highlightValue?: number | null
	types?: ('hot' | 'cold')[]
	variable?: 'duration' | 'size' | 'intensity'
}

const props = defineProps<Props>()
// defaults
const nbins = props.nbins ?? 10
const units = props.units ?? ''
const labelFunc = props.labelFunc ?? ((v: number) => `${v}`)

// responsive width handling
const containerRef = ref<HTMLElement | null>(null)
const width = ref(0) // will be overwritten by ResizeObserver
const height = ref(0) // will be overwritten by ResizeObserver
const resizeObserver = ref<ResizeObserver | null>(null)

onMounted(() => {
	if (!containerRef.value) return
	resizeObserver.value = new ResizeObserver((entries) => {
		let newWidth = 0
		let newHeight = 0
		for (const entry of entries) {
			if (entry.contentRect) {
				newWidth = Math.max(newWidth, Math.floor(entry.contentRect.width))
				newHeight = Math.max(newHeight, Math.floor(entry.contentRect.height))
			}
		}
		width.value = newWidth
		height.value = newHeight
	})
	resizeObserver.value.observe(containerRef.value)
})

onBeforeUnmount(() => {
	if (resizeObserver.value && containerRef.value)
		resizeObserver.value.unobserve(containerRef.value)
	resizeObserver.value = null
})

// compute domain (xmin/xmax) either from props or data extents
const dataExtent = computed(() => {
	const dd = props.data ?? []
	if (!dd.length) return [0, 1]
	return d3.extent(dd) as [number, number]
})

const x0 = computed(() =>
	props.xmin != null ? props.xmin : dataExtent.value[0],
)
const x1 = computed(() =>
	props.xmax != null ? props.xmax : dataExtent.value[1],
)

// defensive: if x0 == x1 expand a bit
const domain = computed(() => {
	let a = x0.value
	let b = x1.value
	if (!isFinite(a) || !isFinite(b)) return [0, 1]
	if (a === b) {
		const delta = Math.abs(a) * 0.01 || 1
		a = a - delta
		b = b + delta
	}
	return [a, b] as [number, number]
})

// Set the fixed bin thresholds based on domain
// The last bin edge is set based on data max to ensure all data is included
// This means the last bin will be wider than the others
const bins = computed(() => {
	const d = props.data ?? []
	const types = props.types ?? []
	const [xmin, xmax] = domain.value

	const step = (xmax - xmin) / (nbins + 1)
	const thresholds = Array.from({ length: nbins }, (_, i) => xmin + i * step)
	thresholds.push(
		dataExtent.value[1] + 0.5 * (dataExtent.value[1] - dataExtent.value[0]),
	)

	const binned = thresholds.slice(0, -1).map((t0, i) => {
		const t1 = thresholds[i + 1]
		const binIdx = d
			.map((val, j) => ({ val, j }))
			.filter(({ val }) => val >= t0 && val < t1)

		const hotCount = binIdx.filter(({ j }) => types[j] === 'hot').length
		const coldCount = binIdx.filter(({ j }) => types[j] === 'cold').length
		const total = binIdx.length || 1

		const binPoints = binIdx.map(({ val }) => val)
		return Object.assign(binPoints, {
			x0: t0,
			x1: t1,
			hotPct: hotCount / total,
			coldPct: coldCount / total,
		})
	})

	if (binned.length > 0) {
		binned[binned.length - 1].x1 = xmax
	}

	return binned
})

// y values expressed as percentage of total data count
const counts = computed(() => bins.value.map((b) => b.length))
const totalCount = computed(() => Math.max(1, props.data?.length ?? 0))
const countsPct = computed(() =>
	counts.value.map((c) => (c / totalCount.value) * 100),
)

// y scale domain: 0 -> auto max or fixed yMaxPct prop
const maxPctAuto = computed(() =>
	countsPct.value.length ? Math.max(...countsPct.value) : 0,
)
const yPctMax = computed(() => {
	if (props.yMaxPct != null) return Math.max(props.yMaxPct, maxPctAuto.value)
	// give a little headroom so bars don't touch top
	return Math.max(1, Math.ceil(maxPctAuto.value * 1.08))
})

// margins + inner dims
const margin = { top: 0, right: 0, bottom: 0, left: 0 }
const innerHeight = computed(() =>
	Math.max(40, height.value - margin.top - margin.bottom),
)
const innerWidth = computed(() =>
	Math.max(40, width.value - margin.left - margin.right),
)

// scales
const xScale = computed(() =>
	d3.scaleLinear().domain(domain.value).range([0, innerWidth.value]),
)
const yScale = computed(() =>
	d3.scaleLinear().domain([0, yPctMax.value]).range([innerHeight.value, 0]),
)

// x-axis tick formatting
// const xTicks = computed(() => xScale.value.ticks(Math.min(2, nbins)))
// const yTicks = computed(() => yScale.value.ticks(5))

const highlightBin = computed(() => {
	if (props.highlightValue == null) return null
	const ret = bins.value.findIndex((b) => {
		return (
			(b.x0 as number) <= props.highlightValue! &&
			(b.x1 as number) > props.highlightValue!
		)
	})
	if (ret < 0) return bins.value.length - 1
	return ret
})

// bar rectangles data (x, width, y, height, pct, count)
const bars = computed(() => {
	const ret = bins.value.map((b, idx) => {
		const x = xScale.value(b.x0 as number)
		const x1p = xScale.value(b.x1 as number)
		const w = Math.max(0, x1p - x)
		const pct = countsPct.value[idx] ?? 0
		const y = Math.max(0, yScale.value(pct))
		const h = Math.max(0, innerHeight.value - y)
		return {
			idx,
			x,
			w,
			y,
			h,
			pct,
			count: counts.value[idx],
			bin0: b.x0,
			bin1: b.x1,
			color: b.hotPct === 0 && b.coldPct === 0 ? 'var(--primary)' : binGradient(
				b.hotPct,
				b.coldPct,
				scssVars.c3sred,
				scssVars.c3sblue,
			), // red→blue
		}
	})
	return ret
})

// optional: animate transitions by giving CSS transitions to rect attrs
// We'll use straightforward attribute binding + CSS transitions on transform/height where possible

// watch for data changes to possibly reset width/height or perform actions
watch(
	() => [props.data, props.xmin, props.xmax, props.nbins],
	() => {
		// nothing special required here, computed values will update
	},
	{ deep: false },
)
</script>

<template>
	<div ref="containerRef" class="histogram-root">
		<IconHourglassHigh v-if="props.variable === 'duration'" />
		<IconDimensions v-else-if="props.variable === 'size'" />
		<IconTemperature v-else-if="props.variable === 'intensity'" />
		<svg class="histogram-svg" role="img">
			<!-- group for plotting area -->
			<g :transform="`translate(${margin.left},${margin.top})`">
				<!-- X axis ticks -->
				<!-- <g
					class="x-axis"
					:transform="`translate(0, ${innerHeight})`"
					v-if="xmin != null && xmax != null"
				>
					<text :x="2" y="12" text-anchor="start">{{ labelFunc(xmin) }}</text>
					<text :x="innerWidth / 2" y="12" text-anchor="middle">
						{{ units }}
					</text>
					<text :x="innerWidth - 2" y="12" text-anchor="end">
						{{ labelFunc(bins[bins.length - 1].x0) }}+
					</text>
				</g> -->

				<!-- Bars (main loop you can customize) -->
				<g class="bars">
					<g
						v-for="b in bars"
						:key="b.idx"
						class="bar-group"
						:transform="`translate(${b.x},0)`"
					>
						<!-- default bar rect -->
						<rect
							class="bar-rect"
							:x="1"
							:y="b.y - 1"
							:width="Math.max(3, b.w - 2)"
							:height="b.h + 1"
							:data-pct="b.pct"
							:data-count="b.count"
							:class="{
								highlight: highlightBin === b.idx,
							}"
							:fill="b.color"
						/>
						<!-- <circle
							:opacity="highlightBin === b.idx ? 1 : 0"
							class="bar-halo"
							:cx="Math.max(1, b.w - 1) / 2"
							:cy="b.y"
							:r="b.w / 3"
						/> -->
					</g>
				</g>
			</g>
		</svg>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

.histogram-root {
	width: 100%;
	height: 100%;
	position: relative;

	.tabler-icon {
		width: min(50%, 3rem);
		height: auto;
		color: white;
		opacity: 0.8;
		position: absolute;
		top: 8px;
		right: 4px;
		pointer-events: none;
		user-select: none;
		z-index: 10;
	}

	/* the container controls svg width via ResizeObserver */
	.histogram-svg {
		z-index: 0;
		width: 100%;
		height: 100%;
		display: block;
		font-family:
			ui-sans-serif,
			system-ui,
			-apple-system,
			'Segoe UI',
			Roboto,
			'Helvetica Neue',
			Arial;
	}
}

/* x axis ticks */
.x-axis text {
	font-size: 11px;
}

/* bars */
.bars .bar-group {
	transition:
		transform 300ms ease,
		opacity 200ms ease;
}

$rate: 0.5 * $animTime;

.bar-rect {
	stroke: black;
	stroke-width: 0.5;
	// fill: $c3sred;
	rx: 2;
	transition: all $rate ease-in-out;

	&.highlight {
		fill: $lightbulb;
		stroke: var(--highlight-hover);
		stroke-width: 1;
		filter: drop-shadow(0 0 2px $lightbulb) drop-shadow(0 0 4px $lightbulb);
	}
}

.bar-halo {
	fill: rgba($lightbulb, 0.33);
	stroke: $lightbulb;
	stroke-width: 1;
	transition: all $rate ease-in-out;
	filter: drop-shadow(0 0 1px $lightbulb) drop-shadow(0 0 2px $lightbulb)
		drop-shadow(0 0 4px $lightbulb) drop-shadow(0 0 8px $lightbulb);
	pointer-events: none;
	user-select: none;
}

.bar-label {
	fill: white;
	font-size: 11px;
	pointer-events: none;
	user-select: none;
}
</style>
