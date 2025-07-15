<script setup lang="ts">
import { computed, watch, ref, onMounted } from 'vue'
import * as d3 from 'd3'
import { FullEvent } from '@/store/store'

const props = defineProps<{ selectedEvent: FullEvent | null }>()

const days = computed(() => props.selectedEvent?.times || [])

const areaData = computed(() => props.selectedEvent?.areas || [])
const peakData = computed(() => props.selectedEvent?.peak_values || [])
const meanData = computed(() => props.selectedEvent?.mean_values || [])
const distData = computed(() => {
	const centroids = props.selectedEvent?.centroids || []
	if (centroids.length < 2) return []
	const [startX, startY] = centroids[0]
	return centroids.map(([x, y]) => Math.hypot(x - startX, y - startY))
})

const margin = { top: 20, right: 0, bottom: 30, left: 0 }

const svgRef = ref<SVGSVGElement | null>(null)
const width = computed(() => {
	const container = svgRef.value
	if (container) {
		const rect = container.getBoundingClientRect()
		return rect.width || 800
	}
    return 800
})
const height = computed(() => {
    const container = svgRef.value
    if (container) {
        const rect = container.getBoundingClientRect()
        return rect.height / 3 || 400
    }
    return 400
})

// Scales
const xScale = computed(() => {
	const sideMargin = (0.5 * width.value) / (days.value.length+1)
	return d3
		.scaleBand()
		.domain(days.value.map((_, i) => i.toString()))
		.range([sideMargin, width.value - sideMargin])
		.padding(0)
})

const areaScale = computed(() =>
	d3
		.scaleLinear()
		.domain([0, d3.max(areaData.value) || 1])
		.range([height.value - margin.bottom, margin.top]),
)
const valueScale = computed(() =>
	d3
		.scaleLinear()
		.domain([273.15, d3.max(peakData.value) || 1])
		.range([height.value - margin.bottom, margin.top]),
)
const distScale = computed(() =>
	d3
		.scaleLinear()
		.domain([0, d3.max(distData.value) || 1])
		.range([height.value - margin.bottom, margin.top]),
)

const transitionDuration = 300
</script>

<template>
	<svg class="graph-container" ref="svgRef">
		<!-- Geographic Area Bar Chart -->
		<g>
			<template v-for="(day, i) in days" :key="day">
				<rect
					:x="xScale(i.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3 - margin.bottom"
					:fill="i % 2 === 0 ? '#f0f0f0' : '#e0e0e0'"
				/>
			</template>
		</g>

		<g>
			<text x="10" y="15">Area</text>
			<template v-for="(value, i) in areaData" :key="i">
				<rect
					:x="xScale(i.toString())"
					:y="areaScale(value)"
					:width="xScale.bandwidth()"
					:height="height - margin.bottom - areaScale(value)"
					fill="#4e79a7"
				/>
			</template>
		</g>

		<!-- Peak and Mean Value Line Chart -->
		<g :transform="`translate(0, ${height})`">
			<text x="10" y="15">Peak & Mean</text>
			<template v-if="peakData.length">
				<polyline
					fill="none"
					stroke="#e15759"
					stroke-width="2"
					:points="
						peakData
							.map(
								(v, i) =>
									`${xScale(i.toString()) + xScale.bandwidth() / 2},${valueScale(v)}`,
							)
							.join(' ')
					"
				/>
			</template>
			<template v-if="meanData.length">
				<polyline
					fill="none"
					stroke="#f28e2b"
					stroke-width="2"
					stroke-dasharray="4"
					:points="
						meanData
							.map(
								(v, i) =>
									`${xScale(i.toString()) + xScale.bandwidth() / 2},${valueScale(v)}`,
							)
							.join(' ')
					"
				/>
			</template>
		</g>

		<!-- dist Chart -->
		<g :transform="`translate(0, ${height * 2})`">
			<text x="10" y="15">dist from start</text>
			<template v-if="distData.length">
				<polyline
					fill="none"
					stroke="#76b7b2"
					stroke-width="2"
					:points="
						distData
							.map(
								(v, i) =>
									`${xScale(i.toString()) + xScale.bandwidth() / 2},${distScale(v)}`,
							)
							.join(' ')
					"
				/>
			</template>
		</g>
	</svg>
</template>

<style scoped>
svg {
	font-family: sans-serif;
	font-size: 12px;
	user-select: none;
    width : 100%;
    height: 100%;
}
text {
	fill: #444;
	font-weight: bold;
}
</style>
