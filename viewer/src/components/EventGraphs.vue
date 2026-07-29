<script setup lang="ts">
import { computed, watch, onBeforeUnmount, onMounted, ref } from 'vue'
import * as d3 from 'd3'

import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore as useTimeStore } from '@/store/timeStore'
import { IconDimensions, IconTemperatureMinus, IconTemperaturePlus, IconCloudRain } from '@tabler/icons-vue'
import { niceNumber } from '@/lib/utils'
import { dateStr } from '@/lib/time-utils'
import { useLabels } from '@/lib/labels'
import ChartDownloadMenu from '@/components/util/ChartDownloadMenu.vue'
import {
	createExportCanvas,
	drawDateAxis,
	downloadCanvas,
	resolveColor,
	AXIS_COLOR,
	GRID_COLOR,
	TICK_COLOR,
	TEXT_COLOR,
	type Rect,
} from '@/lib/chart-export'
import { circle } from 'leaflet'

const $l = useLabels()
const store = useStore()
const eventStore = useEventStore()
const timeStore = useTimeStore()
const props = defineProps<{ selectedEvent: ExtremeEventFull | null }>()
const emits = defineEmits<{
	(event: 'dateSelected', date: number): void
}>()

const days = computed(() => props.selectedEvent?.times || [])
const areaData = computed(() => eventStore.sizesForEvent(props.selectedEvent))
const intensityData = computed(() => {
	// console.log(
	// 	'Intensity data for event',
	// 	props.selectedEvent,
	// 	eventStore.intensitiesForEvent(props.selectedEvent),
	// )
	return eventStore.intensitiesForEvent(props.selectedEvent)
})

const chartTopMargin = 0

const svgRef = ref<SVGSVGElement | null>(null)
const width = ref(100)
const height = ref(200)

// Scales
const xScale = computed(() => {
	const sideMargin = (0.5 * width.value) / (days.value.length + 1)
	return d3
		.scaleBand()
		.domain(days.value.map((_, i) => i.toString()))
		.range([sideMargin, width.value - sideMargin])
		.padding(0)
})

const sizeScale = computed(() => {
	// console.log('Area data for sizeScale:', areaData.value)
	return d3
		.scaleLinear()
		.domain([0, d3.max(areaData ? areaData.value : []) || 1])
		.range([height.value - 3, chartTopMargin + 3])
})
const intensityScale = computed(() =>
	d3
		.scaleLinear()
		.domain([
			d3.min(intensityData.value) || 0,
			d3.max(intensityData.value) || 1,
		])
		.range([height.value - 5, chartTopMargin + 5]),
)

const selectedIndex = computed(() => {
	if (!props.selectedEvent) return -1
	const selectedTime = timeStore.selectedTime
	return props.selectedEvent.times.findIndex(
		(d) => d === selectedTime.getTime(),
	)
})

onMounted(() => {
	const observer = new ResizeObserver((entries) => {
		for (const entry of entries) {
			width.value = entry.contentRect.width
			height.value = entry.contentRect.height
		}
		// console.log('SVG resized:', entries, width.value, height.value)
	})
	if (!svgRef.value) return
	observer.observe(svgRef.value)

	onBeforeUnmount(() => observer.disconnect())
})

watch(
	() => [
		props.selectedEvent,
		areaData.value,
		intensityData.value,
		svgRef.value,
	],
	() => {
		// console.log('EventGraphs: event or areaData changed')
		// Reset scales when event changes
		width.value = svgRef.value?.clientWidth || 100
		height.value = svgRef.value?.clientHeight || 100
	},
)

const eventType = computed(() => props.selectedEvent?.event_type || 'unknown')

function downloadCSV() {
	const intensityUnits =
		props.selectedEvent?.event_type === 'hot'
			? eventStore.heatIntensityUnits
			: props.selectedEvent?.event_type === 'cold'
				? eventStore.coldIntensityUnits
				: eventStore.wetIntensityUnits
	const headers = [
		'date',
		`intensity_${intensityUnits.replace(/[^a-zA-Z0-9]/g, '_')}`,
		`size_${eventStore.sizeUnits.replace(/[^a-zA-Z0-9]/g, '_')}`,
	]
	const rows = days.value.map((t, i) => [
		new Date(t).toISOString().slice(0, 10),
		intensityData.value[i] ?? '',
		areaData.value[i] ?? '',
	])
	const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
	const blob = new Blob([csv], { type: 'text/csv' })
	const url = URL.createObjectURL(blob)
	const a = document.createElement('a')
	a.href = url
	a.download = (props.selectedEvent?.id ?? 'event') + '-timeseries.csv'
	a.click()
	URL.revokeObjectURL(url)
}

function downloadImage() {
	const dayList = days.value
	if (!dayList.length) return
	const type = eventType.value
	const themeColor = resolveColor(
		type === 'hot'
			? 'var(--theme-hot-primary)'
			: type === 'cold'
				? 'var(--theme-cold-primary)'
				: 'var(--primary)',
	)

	const { canvas, ctx, width: cw, height: ch } = createExportCanvas()
	const left = 80
	const right = 28
	const plot1: Rect = { x: left, y: 74, w: cw - left - right, h: 236 }
	const plot2: Rect = { x: left, y: 424, w: cw - left - right, h: 236 }

	const n = dayList.length
	const bandCenter = (plot: Rect, i: number) => {
		const sideMargin = (0.5 * plot.w) / (n + 1)
		const bw = (plot.w - 2 * sideMargin) / n
		return plot.x + sideMargin + i * bw + bw / 2
	}
	const bandWidth = (plot: Rect) => {
		const sideMargin = (0.5 * plot.w) / (n + 1)
		return (plot.w - 2 * sideMargin) / n
	}

	const titleFont =
		'600 16px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
	const tickFont =
		'12px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

	const drawFrame = (
		plot: Rect,
		title: string,
		yLo: number,
		yHi: number,
		yUnits: string,
	) => {
		const span = yHi - yLo || 1
		const sy = (v: number) => plot.y + plot.h - ((v - yLo) / span) * plot.h
		// title
		ctx.fillStyle = TEXT_COLOR
		ctx.font = titleFont
		ctx.textAlign = 'left'
		ctx.textBaseline = 'alphabetic'
		ctx.fillText(title, plot.x, plot.y - 18)
		// y gridlines + ticks
		ctx.font = tickFont
		for (let k = 0; k <= 4; k++) {
			const v = yLo + (span * k) / 4
			const py = sy(v)
			ctx.strokeStyle = GRID_COLOR
			ctx.lineWidth = 1
			ctx.beginPath()
			ctx.moveTo(plot.x, py)
			ctx.lineTo(plot.x + plot.w, py)
			ctx.stroke()
			ctx.fillStyle = TICK_COLOR
			ctx.textAlign = 'right'
			ctx.textBaseline = 'middle'
			ctx.fillText(String(niceNumber(v)), plot.x - 7, py)
		}
		// frame
		ctx.strokeStyle = AXIS_COLOR
		ctx.lineWidth = 1.5
		ctx.beginPath()
		ctx.moveTo(plot.x, plot.y)
		ctx.lineTo(plot.x, plot.y + plot.h)
		ctx.lineTo(plot.x + plot.w, plot.y + plot.h)
		ctx.stroke()
		// y axis title
		ctx.save()
		ctx.fillStyle = TEXT_COLOR
		ctx.font =
			'600 13px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
		ctx.translate(20, plot.y + plot.h / 2)
		ctx.rotate(-Math.PI / 2)
		ctx.textAlign = 'center'
		ctx.textBaseline = 'top'
		ctx.fillText(yUnits, 0, 0)
		ctx.restore()
		drawDateAxis(ctx, plot, dayList, (i) => bandCenter(plot, i))
		return sy
	}

	const intensityUnits =
		type === 'hot'
			? eventStore.heatIntensityUnits
			: type === 'cold'
				? eventStore.coldIntensityUnits
				: eventStore.wetIntensityUnits

	const iVals = intensityData.value
	const aVals = areaData.value
	const iLo = d3.min(iVals) ?? 0
	const iHi = d3.max(iVals) ?? 1
	const aHi = d3.max(aVals) ?? 1

	const intensityTitle =
		type === 'hot' || type === 'cold' ? $l.value.eventTempTS : $l.value.eventWetTS

	// Panel 1: intensity (line + points)
	const syI = drawFrame(plot1, intensityTitle, iLo, iHi, intensityUnits)
	ctx.save()
	ctx.beginPath()
	ctx.rect(plot1.x, plot1.y - 6, plot1.w, plot1.h + 6)
	ctx.clip()
	ctx.strokeStyle = themeColor
	ctx.lineWidth = 2
	ctx.beginPath()
	iVals.forEach((v, i) => {
		const px = bandCenter(plot1, i)
		const py = syI(v)
		if (i === 0) ctx.moveTo(px, py)
		else ctx.lineTo(px, py)
	})
	ctx.stroke()
	ctx.fillStyle = themeColor
	iVals.forEach((v, i) => {
		ctx.beginPath()
		ctx.arc(bandCenter(plot1, i), syI(v), 4, 0, 2 * Math.PI)
		ctx.fill()
	})
	ctx.restore()

	// Panel 2: size (bars)
	const syA = drawFrame(plot2, $l.value.eventSizeTS, 0, aHi, eventStore.sizeUnits)
	ctx.save()
	ctx.beginPath()
	ctx.rect(plot2.x, plot2.y, plot2.w, plot2.h)
	ctx.clip()
	const bw = Math.max(1, bandWidth(plot2) - 1)
	ctx.fillStyle = themeColor
	aVals.forEach((v, i) => {
		const cx = bandCenter(plot2, i)
		const top = syA(v)
		ctx.fillRect(cx - bw / 2, top, bw, plot2.y + plot2.h - top)
	})
	ctx.restore()

	downloadCanvas(canvas, (props.selectedEvent?.id ?? 'event') + '-timeseries')
}
</script>

<template>
	<div class="event-graphs-root">
		<div class="loading" v-if="store.eventSoftLoadingCount > 0">
			<div class="spinner-container">
				<div class="spinner-ring"></div>
				<div class="spinner-ring-inner"></div>
			</div>
		</div>
		<div class="chart">
			<h1 class="chart-title">
				{{ selectedEvent?.event_type === 'hot' || selectedEvent?.event_type === 'cold' ? $l.eventTempTS : $l.eventWetTS }}
			</h1>
			<div class="axis">
				<div class="label mono">
					{{ niceNumber(intensityScale.domain()[0]) }}
				</div>
				<span class="unit-icon"
					>
					<IconTemperaturePlus v-if="selectedEvent?.event_type === 'hot'" class="icon" :class="{ [eventType]: true }" />
					<IconTemperatureMinus v-else-if="selectedEvent?.event_type === 'cold'" class="icon" :class="{ [eventType]: true }" />
					<IconCloudRain v-else class="icon" :class="{ [eventType]: true }" />
					
					{{
						selectedEvent?.event_type === 'hot'
							? eventStore.heatIntensityUnits
							: selectedEvent?.event_type === 'cold'
								? eventStore.coldIntensityUnits
								: eventStore.wetIntensityUnits
					}}
					</span
				>
				<div class="label mono">
					{{ niceNumber(intensityScale.domain()[1]) }}
				</div>
			</div>
			<svg class="intensity-chart" ref="svgRef" id="event-graph-width-el">
				<defs>
					<filter id="egBarShadow" height="130%">
						<feDropShadow
							dx="1"
							dy="1"
							stdDeviation="1"
							flood-color="rgba(0, 0, 0, 0.1)"
						/>
					</filter>
				</defs>
				<rect
					v-if="selectedIndex >= 0"
					:x="xScale(selectedIndex.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					class="graph-bg selected"
				/>
				<g>
					<template v-if="intensityData.length">
						<polyline
							class="intensity-line"
							:class="{ [eventType]: true }"
							fill="none"
							stroke-width="2"
							:points="
								intensityData
									.map(
										(value, i) =>
											`${xScale(i.toString())! + xScale.bandwidth() / 2},${intensityScale(
												value,
											)}`,
									)
									.join(' ')
							"
						/>
						<circle 
							v-for="(value, i) in intensityData" 
							:key="i"
							:cx="xScale(i.toString())! + xScale.bandwidth() / 2"
							:cy="intensityScale(value)"
							r="5"
							:class="{
								selected: i === selectedIndex,
								[eventType]: true,
							}"
							class="line-point"
							@click="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							@keydown.space.prevent="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							v-tooltip="dateStr(new Date(props.selectedEvent?.times[i] || 0)) + ': ' + niceNumber(value) + ' ' + (selectedEvent?.event_type === 'hot' ? eventStore.heatIntensityUnits : selectedEvent?.event_type === 'cold' ? eventStore.coldIntensityUnits : eventStore.wetIntensityUnits)"	/>
					</template>
				</g>
			</svg>
		</div>
		<div class="spacer"></div>
		<div class="chart">
			<h1 class="chart-title">
				{{ $l.eventSizeTS }}
			</h1>
			<div class="axis">
				<div class="label mono">{{ niceNumber(sizeScale.domain()[0]) }}</div>
				<span class="unit-icon"
					><IconDimensions class="icon" :class="{ [eventType]: true }" />{{
						eventStore.sizeUnits
					}}</span
				>
				<div class="label mono">{{ niceNumber(sizeScale.domain()[1]) }}</div>
			</div>
			<svg class="size-chart">
				<defs>
					<filter id="egBarShadow" height="130%">
						<feDropShadow
							dx="1"
							dy="1"
							stdDeviation="1"
							flood-color="rgba(0, 0, 0, 0.1)"
						/>
					</filter>
				</defs>
				<rect
					v-if="selectedIndex >= 0"
					:x="xScale(selectedIndex.toString())"
					:y="0"
					:width="xScale.bandwidth()"
					:height="height * 3"
					class="graph-bg selected"
				/>

				<g>
					<template v-for="(value, i) in areaData" :key="i">
						<rect
							:x="xScale(i.toString())"
							:y="sizeScale(value)"
							:width="xScale.bandwidth() - 0.5"
							:height="height - sizeScale(value)"
							:class="{
								selected: i === selectedIndex,
								[eventType]: true,
							}"
							vector-effect="non-scaling-stroke"
							class="area-bar"
							filter="url(#egBarShadow)"
							@click="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							@keydown.space.prevent="emits('dateSelected', props.selectedEvent?.times[i] || 0)"
							v-tooltip="dateStr(new Date(props.selectedEvent?.times[i] || 0)) + ': ' + niceNumber(value) + ' ' + eventStore.sizeUnits"
						</rect>
					</template>
				</g>
			</svg>
		</div>
		<ChartDownloadMenu
			:disabled="!days.length"
			@csv="downloadCSV"
			@image="downloadImage"
		/>
		<slot></slot>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.event-graphs-root {
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	padding: 0.5rem;

	.loading {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: var(--panel-bg-night);
		background-image: var(--panel-bg);
		z-index: 10;
	}

	&.loading {
		flex: 0 0 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.spacer {
		margin: 0.25rem 0;
		width: 100%;
		flex: 0 0 1px;
		background-color: var(--divider);
	}

	.chart {
		z-index: 0;

		flex: 0 1 calc(50% - 0.5rem); /* allow shrinking */
		max-height: calc(50% - 0.5rem);

		width: 100%; /* let flex handle it */
		min-width: 0; /* crucial for flex children that need to shrink */
		position: relative;
		display: flex;
		flex-direction: row;
		align-items: stretch; /* default, just in case */
		justify-content: center;

		.axis {
			flex: 1 0 2.5rem;
			height: 100%;
			display: flex;
			flex-direction: column-reverse;
			justify-content: space-between;
			align-items: center;
			font-size: 0.85rem;

			.unit-icon {
				display: flex;
				align-items: center;
				gap: 0.25rem;
				color: var(--text-secondary);
				text-align: center;
			}

			.label {
				user-select: none;
				color: var(--text-secondary);
				flex: 0 0 auto;
				flex-direction: row;
			}

			.icon {
				flex: 0 0 1.25rem;
				width: 1.25rem;
				height: 1.25rem;
				margin: 0.25rem 0;

				display: flex;
				align-items: center;
				justify-content: center;

				&.hot {
					color: var(--theme-hot-primary);
				}
				&.cold {
					color: var(--theme-cold-primary);
				}
				&.wet {
					color: var(--primary);
				}
			}
		}

		.size-chart,
		.intensity-chart {
			flex: 1 1 75%;
			background: var(--panel-bg);
			box-shadow: inset 2px 2px 8px rgba(0, 0, 0, 0.2);
			// display: block;
			// width: 100%; /* remove !important */
			// height: 100%; /* optional: depends on parent */
			// max-width: 100%;
			// max-height: 100%;
		}
	}
}

.size-chart,
.intensity-chart {
	font-family: sans-serif;
	font-size: 12px;
	user-select: none;

	.area-bar {
		cursor: pointer;
		&.hot {
			fill: var(--theme-hot-primary);
		}
		&.cold {
			fill: var(--theme-cold-primary);
		}
		&.wet {
			fill: var(--primary);
		}
		&.selected {
			fill: var(--primary-glass-shine);
			&.hot {
				fill: var(--theme-hot-primary-glass-shine);
			}
			&.cold {
				fill: var(--theme-cold-primary-glass-shine);
			}
		}
	}

	.line-point {
		cursor: default;
		stroke: none;
		opacity: 0;
		&.selected {
			cursor: pointer;
			opacity: 1;
			r:4;
			fill: var(--primary-glass-shine);
			&.hot {
				fill: var(--theme-hot-primary-glass-shine);
			}
			&.cold {
				fill: var(--theme-cold-primary-glass-shine);
			}
		}
	}

	.intensity-line {
		&.hot {
			stroke: var(--theme-hot-primary);
		}
		&.cold {
			stroke: var(--theme-cold-primary);
		}
		&.wet {
			stroke: var(--primary);
		}
	}

	.graph-bg {
		fill: white;
		cursor: pointer;
	}
}
</style>
