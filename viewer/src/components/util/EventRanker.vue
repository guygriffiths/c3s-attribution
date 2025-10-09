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
		console.log('Ranked events:', [...rankedEvents.value].splice(0, 10).map((e) => `events/event-${e.id}.json`).join(' '))
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

const selectFinal = ref(false)
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
					rankElement.scrollTo({ top: rankElement.offsetTop - scroller.offsetHeight / 2, behavior: 'smooth' })
				}
				selectFinal.value = false
			} else if (idx < 0) {
				// If the selected event is not in the ranked list, scroll to the very bottom
				scroller?.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' })
				selectFinal.value = true
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
					:title="`Duration: ${eventStore.durationForEvent(rankedEvents[i - 1])} days\nSize: ${eventStore.sizeForEvent(rankedEvents[i - 1]).toFixed(2)} km²\nIntensity: ${eventStore.intensityForEvent(rankedEvents[i - 1]).toFixed(2)}`"
				></div>
				<div
					v-if="eventsInRanker < props.events.length"
					class="rank"
					:class="{
						odd: topN % 2 === 1,
						selected: selectFinal,
					}"
					:title="
						eventStore.selectedEvent
							? `Duration: ${eventStore.durationForEvent(eventStore.selectedEvent)} days\nSize: ${eventStore.sizeForEvent(eventStore.selectedEvent).toFixed(2)} km²\nIntensity: ${eventStore.intensityForEvent(eventStore.selectedEvent).toFixed(2)}`
							: ''
					"
				></div>
				<svg
					width="100%"
					ref="eventRankerSvgRef"
					:height="
						ROW_SIZE *
						(eventsInRanker < props.events.length
							? eventsInRanker + 1
							: eventsInRanker)
					"
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
					<rect
						v-if="
							eventsInRanker < props.events.length && eventStore.selectedEvent
						"
						class="ranked-event"
						x="0"
						y="0"
						:transform="`translate(0, ${eventsInRanker * ROW_SIZE + 0.5 * ROW_SIZE - 0.5 * heightScale(eventStore.sizeForEvent(eventStore.selectedEvent) || 0)})`"
						:width="
							widthScale(
								eventStore.durationForEvent(eventStore.selectedEvent) || 0,
							)
						"
						:height="
							heightScale(
								eventStore.sizeForEvent(eventStore.selectedEvent) || 0,
							)
						"
						:fill="
							eventStore.colorForEvent(eventStore.selectedEvent as any as ExtremeEvent) ||
							scssVars.c3sred
						"
					/>
					<text
						v-for="(event, idx) in rankedEvents"
						:key="`text-${idx}`"
						class="ranked-event"
						:class="event.event_type"
						x="0"
						y="0"
						:transform="`translate(${widthScale(eventStore.durationForEvent(event)) + 4}, ${idx * ROW_SIZE + 18})`"
						font-size="14"
					>
						{{ idx + 1 }}
					</text>
					<text
						v-if="eventsInRanker < props.events.length"
						class="ranked-event"
						:class="eventStore.selectedEvent?.event_type || 'mixed'"
						x="0"
						y="0"
						:transform="`translate(${eventStore.selectedEvent ? widthScale(eventStore.durationForEvent(eventStore.selectedEvent)) + 4 : 10}, ${eventsInRanker * ROW_SIZE + 14})`"
						font-size="14"
					>
						{{ topN + 1 }} - {{ props.events.length }}
					</text>
				</svg>
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

.scroller {
	margin: 0;
	height: 100%;
	overflow-y: auto;
	position: relative;
	.scrollee {
		min-height: calc(20 * $rankedEventHeight);
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
				background-color: color.adjust($panelBg, $lightness: -5%);
			}

			&.hovering,
			&:hover {
				background-color: color.adjust($panelBg, $lightness: -10%);
				box-shadow: 0 0 10px rgba($c3sred, 0.5);
			}

			&.selected {
				border-top: 2px solid $c3sred;
				border-bottom: 2px solid $c3sred;
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
			&.mixed {
				stroke-width: 0;
				fill: black;
			}
		}
	}
}
</style>
