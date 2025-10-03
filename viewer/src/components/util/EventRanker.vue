<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useStore as useEventStore } from '@/store/eventStore'
import scssVars from '@/assets/styles/scssVars.module.scss'
import * as d3 from 'd3'
const eventStore = useEventStore()

const ROW_SIZE = 24
const props = defineProps<{
	events: ExtremeEvent[] // The events to rank
	// The metric to rank by
	sortFunc: (a: ExtremeEvent, b: ExtremeEvent) => number
	topN: number
}>()
const eventRankerSvgRef = ref<SVGSVGElement | null>(null)
const scrollerRef = ref<HTMLDivElement | null>(null)
const width = ref(300)
const height = ref(ROW_SIZE * 10)

watch(eventRankerSvgRef, (el) => {
	if (!el) return
	const ro = new ResizeObserver(([entry]) => {
		width.value = entry.contentRect.width > 40 ? entry.contentRect.width : 50
	})
	ro.observe(el)
})

watch(scrollerRef, (el) => {
	if (!el) return
	const ro = new ResizeObserver(([entry]) => {
		height.value = entry.contentRect.height
	})
	ro.observe(el)
})

const widthScale = computed(() => {
	// Find the max duration in the currently filtered events
	return d3
		.scaleLinear()
		.domain(eventStore.durationRange)
		.range([12, width.value - 28])
		.clamp(true)
})
const heightScale = computed(() => {
	// Find the max duration in the currently filtered events
	return d3
		.scaleLinear()
		.domain(eventStore.sizeRange)
		.range([2, 20])
		.clamp(true)
})

const rankedEvents = ref<ExtremeEvent[]>([])
watch(
	() => props.events,
	() => {
		rankedEvents.value = [...(props.events || [])]
			.sort(props.sortFunc)
			.splice(0, props.topN)
	},
	{ deep: false },
)

const nRanksToShow = ref(props.events.length)
watch(rankedEvents, (newVal) => {
	nRanksToShow.value = newVal.length
})

const selectEvent = (event: ExtremeEvent | null) => {
	if (event) {
		eventStore.selectEvent(event.id)
	}
}

watch(
	() => eventStore.selectedEventId,
	(newVal) => {
		if (newVal) {
			// Ensure the selected event is in view
			const idx = rankedEvents.value.findIndex((e) => e.id === newVal)
			const scroller = scrollerRef.value
			if (scroller && idx >= 0) {
				const rankElement = scroller.children[0].children[idx]
				if (rankElement) {
					// console.log('rankElement', rankElement)
					rankElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
				}
			}
		}
	},
)

const eventsInRanker = computed(() => Math.min(props.topN, props.events.length))
</script>

<template>
	<div class="event-ranker">
		<div class="scroller" ref="scrollerRef">
			<div class="scrollee">
				<div
					v-for="i in eventsInRanker"
					:key="i"
					class="rank"
					:class="{
						odd: i % 2 === 1,
						selected: rankedEvents[i - 1]?.id === eventStore.selectedEventId,
						hovering: rankedEvents[i - 1]?.id === eventStore.hoveringEventId,
					}"
					@click="selectEvent(rankedEvents[i - 1] || null)"
				></div>
				<svg
					width="100%"
					ref="eventRankerSvgRef"
					:height="ROW_SIZE * eventsInRanker"
					preserveAspectRatio="none"
					style="pointer-events: none"
				>
					<rect
						v-for="(event, idx) in rankedEvents"
						class="ranked-event"
						:key="idx"
						x="0"
						y="0"
						:transform="`translate(0, ${idx * ROW_SIZE + 0.5 * ROW_SIZE - 0.5 * heightScale(eventStore.sizeForEvent(event) || 0)})`"
						:width="widthScale(eventStore.durationForEvent(event) || 0)"
						:height="heightScale(eventStore.sizeForEvent(event) || 0)"
						:fill="eventStore.colorForEvent(event) || scssVars.c3sred"
					/>
					<text
						v-for="(event, idx) in rankedEvents"
						:key="`text-${idx}`"
						class="ranked-event"
						:class="event.event_type"
						x="0"
						y="0"
						:transform="`translate(${widthScale(event.duration) + 4}, ${idx * ROW_SIZE + 18})`"
						font-size="14"
					>
						{{ idx + 1 }}
					</text>
				</svg>
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.scroller {
	margin: 0;
	height: 100%;
	overflow-y: auto;
	position: relative;
	.scrollee {
		svg {
			position: absolute;
			top: 0;
			left: 0;
			height: auto;
			background-color: transparent;
		}
		display: flex;
		flex-direction: column;

		.rank {
			flex: 0 0 $rankedEventHeight;
			min-height: $rankedEventHeight;
			background-color: $panelBg;
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: flex-end;
			width: 100%;
			cursor: pointer;

			&.odd {
				background-color: darken($panelBg, 5%);
			}

			&.hovering,
			&:hover {
				background-color: darken($panelBg, 10%);
				box-shadow: 0 0 10px rgba($c3sred, 0.5);
			}

			&.selected {
				border: 2px solid $c3sred;
				box-shadow: 0 0 10px rgba($c3sred, 0.5);
			}

			p {
				margin: 0;
				padding: 0 0.5rem;
			}
		}

		$rate: $animTime * 0.5;
		.ranked-event {
			position: relative;
			transition:
				x $rate ease-out,
				all $rate ease-out;
			rx: 2;
			stroke: black;
			stroke-width: 0.5;

			&.hot {
				stroke-width: 0;
				fill: $c3sred !important;
			}
			&.cold {
				stroke-width: 0;
				fill: $c3sblue !important;
			}
		}
	}
}
</style>
