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
import { colorMixer } from '@/lib/utils'
import { getBins } from '@/lib/histo-utils'
import scssVars from '@/assets/styles/scssVars.module.scss'
import { niceNumber } from '@/lib/utils'

type Props = {
	data: number[]
	bins?: any[]
	xmin: number
	xmax: number
	nbins?: number
	yMaxCount?: number | null
	highlightValue?: number | null
	types?: EventType[]
	variable?: Variable
	hasTail?: boolean
	title?: string
}

const props = defineProps<Props>()
// defaults
const nbins = props.nbins ?? 10

const bins = ref<any[] | null>([])
watch(
	() => [props.data, props.xmin, props.xmax, props.types, props.bins],
	() => {
		requestAnimationFrame(() => {
			const hasTail = props.hasTail ?? false
			bins.value =
				props.bins !== null && props.bins !== undefined
					? props.bins
					: getBins(
							props.data,
							props.types ?? [],
							props.xmin,
							props.xmax,
							nbins,
							hasTail,
						)
		})
	},
	{ immediate: true },
)

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

// y values expressed as percentage of total data count
const counts = computed(() => bins.value!.map((b) => b.length))
const totalCount = computed(() =>
	props.bins
		? props.bins.reduce((acc, b) => acc + b.length, 0)
		: Math.max(1, props.data?.length ?? 0),
)

// y scale domain: 0 -> auto max or fixed yMaxPct prop
const maxCountAuto = computed(() =>
	counts.value.length ? Math.max(...counts.value) : 0,
)
const yMax = computed(() => {
	if (props.yMaxCount != null)
		return Math.max(props.yMaxCount, maxCountAuto.value)
	// give a little headroom so bars don't touch top
	return Math.max(1, Math.ceil(maxCountAuto.value * 1.08))
})

// margins + inner dims
const margin = { top: 12, right: 0, bottom: 0, left: 0 }
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
	d3.scaleLinear().domain([0, yMax.value]).range([innerHeight.value, 0]),
)

// x-axis tick formatting
// const xTicks = computed(() => xScale.value.ticks(Math.min(2, nbins)))
// const yTicks = computed(() => yScale.value.ticks(5))

const highlightBin = computed(() => {
	if (props.highlightValue == null) return null
	const ret = bins.value!.findIndex((b) => {
		return (
			(b.x0 as number) <= props.highlightValue! &&
			(b.x1 as number) > props.highlightValue!
		)
	})
	if (ret < 0) return bins.value!.length - 1
	return ret
})

// bar rectangles data (x, width, y, height, pct, count)
const bars = computed(() => {
	const ret = bins.value!.map((b, idx) => {
		const x = xScale.value(b.x0 as number)
		const x1p = xScale.value(b.x1 as number)
		const w = Math.max(0, x1p - x)
		const count = counts.value[idx] ?? 0
		const y = Math.max(0, yScale.value(count))
		const h = Math.max(0, innerHeight.value - y)
		return {
			idx,
			x,
			w,
			y,
			h,
			pct: (count / totalCount.value) * 100,
			count,
			bin0: b.x0,
			bin1: b.x1,
			endless: b.endless,
			color:
				b.coldPct === 0 && b.hotPct === 0
					? 'var(--primary)'
					: b.coldPct === 0
						? 'var(--theme-hot-primary)'
						: b.hotPct === 0
							? 'var(--theme-cold-primary)'
							: colorMixer(scssVars.c3sred, b.hotPct, scssVars.c3sblue), // red→blue
		}
	})
	return ret
})

const tooltipForBin = (b: any) => {
	return {
		content: `Range: ${b.endless ? '>' : '['}${niceNumber(b.bin0)} ${b.endless ? '' : ', ' + niceNumber(b.bin1) + ')'}<br />Count: ${b.count}<br />Percentage: ${niceNumber(b.pct)}%`,
		html: true,
	}
}
</script>

<template>
	<div ref="containerRef" class="histogram-root">
		<h1 class="chart-title" v-if="props.title">{{ props.title }}</h1>
		<svg class="histogram-svg" role="img">
			<filter id="histoBarShadow" height="130%">
				<feDropShadow
					dx="1"
					dy="1"
					stdDeviation="2"
					flood-color="rgba(0, 0, 0, 0.3)"
				/>
			</filter>
			<!-- group for plotting area -->
			<g :transform="`translate(${margin.left},${margin.top})`">
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
							:y="b.y - 3"
							:width="Math.max(3, b.w - 2)"
							:height="b.h + 3"
							:class="{
								highlight: highlightBin === b.idx,
							}"
							:fill="b.color"
							filter="url(#histoBarShadow)"
							v-tooltip="tooltipForBin(b)"
						/>
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

$rate: 0s; //0.5 * $animTime;
/* bars */
.bars .bar-group {
	transition:
		transform $rate ease,
		opacity $rate ease;
}

.bar-rect {
	// stroke: black;
	// stroke-width: 0.5;
	// fill: $c3sred;
	// rx: 2;
	transition: all $rate ease-in-out;

	&.highlight {
		fill: $lightbulb;
		stroke: var(--highlight-hover);
		stroke-width: 1;
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
	fill: var(--primary-selected);
	font-size: 11px;
	pointer-events: none;
	user-select: none;
}
</style>
