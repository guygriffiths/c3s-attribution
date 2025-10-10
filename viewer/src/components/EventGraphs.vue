<script setup lang="ts">
import { computed, ComputedRef, ref } from 'vue'
import * as d3 from 'd3'

const props = defineProps<{ selectedEvent: ExtremeEventFull | null }>()
const emits = defineEmits<{
	(event: 'dateSelected', date: Date): void
}>()

const days = computed(() => props.selectedEvent?.times || [])
const areaData = computed(
	() => props.selectedEvent?.slices.map((s) => s.length) || [],
)
const maxData = computed(() => props.selectedEvent?.max_values || [])
const meanData = computed(() => props.selectedEvent?.mean_values || [])
const minData = computed(() => props.selectedEvent?.min_values || [])

const distData = computed(() => {
	const centroids = props.selectedEvent?.centroids || []
	if (centroids.length < 2) return []
    // @ts-ignore
	const [startX, startY] = centroids[0]
	return centroids.map(([x, y]) =>
		Math.sqrt((x - startX) ** 2 + (y - startY) ** 2),
	)
})

const chartTopMargin = 20

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
	const sideMargin = (0.5 * width.value) / (days.value.length + 1)
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
		.range([height.value, chartTopMargin]),
)
const valueScale = computed(() =>
	d3
		.scaleLinear()
		.domain([303.15, d3.max(maxData.value) || 1])
		.range([height.value, chartTopMargin]),
)
const latScale = computed(() =>
	d3
		.scaleLinear()
		.domain([d3.min(distData.value) || 0, d3.max(distData.value) || 1])
		.range([height.value, chartTopMargin]),
)

</script>

<template>
	<svg class="graph-container" ref="svgRef">
		<transition-group
			name="graph-bg-transition"
			tag="g"
			:style="{ transform: 'scaleY(-1) translateY(-100%)' }"
		>
			<template v-for="(day, i) in days" :key="day">
				<rect
					:x="xScale(i.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					:opacity="i % 2 === 0 ? 0.075 : 0.05"
					:fill="props.selectedEvent?.color || '#f0f0f0'"
					@click="emits('dateSelected', day)"
				/>
			</template>
		</transition-group>

		<g :transform="`translate(0, ${height * 2})`">
			<text x="10" y="15">Area</text>
			<template v-for="(value, i) in areaData" :key="i">
				<rect
					:x="xScale(i.toString())"
					:y="areaScale(value)"
					:width="xScale.bandwidth()"
					:height="height - areaScale(value)"
					:fill="props.selectedEvent?.color || '#f0f0f0'"
					stroke="white"
					:stroke-width="2"
					vector-effect="non-scaling-stroke"
				/>
			</template>
		</g>

		<!-- Peak and Mean Value Line Chart -->
		<g :transform="`translate(0, ${height})`">
			<text x="10" y="15">Peak & Mean</text>
			<template v-if="maxData.length">
				<polyline
				<polyline
					fill="none"
					stroke="#e15759"
					stroke-width="2"
					:points="
						maxData
							.map(
								(v, i) =>
									`${xScale(i.toString())! + xScale.bandwidth() / 2},${valueScale(v)}`,
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
									`${xScale(i.toString())! + xScale.bandwidth() / 2},${valueScale(v)}`,
							)
							.join(' ')
					"
				/>
			</template>
		</g>

		<!-- dist Chart -->
		<g :transform="`translate(0, ${0})`">
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
									`${xScale(i.toString())! + xScale.bandwidth() / 2},${latScale(v)}`,
							)
							.join(' ')
					"
				/>
			</template>
		</g>
	</svg>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

svg {
	font-family: sans-serif;
	font-size: 12px;
	user-select: none;
	width: 100%;
	height: 100%;

	.graph-bg-transition-enter-active {
		transition: all $animTime ease-in-out calc($animTime + $settleTime);
	}
	.graph-bg-transition-leave-active {
		transition: all $animTime ease-in-out;
	}
	.graph-bg-transition-enter-from,
	.graph-bg-transition-leave-to {
		height: 0;
	}
	.graph-bg-transition-enter-to,
	.graph-bg-transition-leave-from {
		height: 100%;
	}
}
text {
	fill: #444;
	font-weight: bold;
}
</style>
