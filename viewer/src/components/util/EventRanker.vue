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
	nRowsToShow?: number
}>()
const eventRankerSvgRef = ref<SVGSVGElement | null>(null)
const scrollerRef = ref<HTMLDivElement | null>(null)
const width = ref(300)
const nRowsToShow = ref(props.nRowsToShow ?? 10)
const height = ref(ROW_SIZE * nRowsToShow.value)

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
		.range([12, width.value - 40])
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
	() => [props.events, props.sortFunc],
	() => {
		rankedEvents.value = [...(props.events || [])].sort(props.sortFunc)
		// console.log('Ranked events:', [...rankedEvents.value].splice(0, 10).map((e) => `events/event-${e.id}.json`).join(' '))
	},
	{ deep: false },
)

const selectEvent = (event: ExtremeEvent | null) => {
	if (event) {
		eventStore.selectEvent(event, true)
	}
}

const selectFinal = ref(false)
watch(
	() => eventStore.selectedEventId,
	(newVal) => {
		const scroller = scrollerRef.value
		if (newVal) {
			// Ensure the selected event is in view
			const idx = rankedEvents.value.findIndex((e) => e.id === newVal)
			if (scroller && idx >= 0 && idx <= props.topN) {
				const rankElement = scroller.children[0].children[idx]
				if (rankElement) {
					// console.log('rankElement', rankElement)
					// rankElement.scrollTo({ top: ROW_SIZE * idx, behavior: 'smooth' })
					rankElement.scrollIntoView({
						behavior: 'smooth',
						block: 'center',
						// @ts-ignore
						container: 'nearest',
					})
				}
				selectFinal.value = false
			} else if (idx < 0 || idx > props.topN) {
				// If the selected event is not in the ranked list, scroll to the very bottom
				scroller?.scrollTo({
					top: scroller.scrollHeight + ROW_SIZE * 2,
					behavior: 'smooth',
				})
				selectFinal.value = true
			}
		} else {
			scroller?.scrollTo({ top: 0, behavior: 'smooth' })
			selectFinal.value = false
		}
	},
)

const eventsInRanker = computed(() => Math.min(props.topN, props.events.length))

const selectedIndex = computed(() => {
	if (!eventStore.selectedEvent) return -1
	return (
		rankedEvents.value.findIndex((e) => e.id === eventStore.selectedEventId) + 1
	)
})
</script>

<template>
	<div class="event-ranker-root">
		<div class="scroller" ref="scrollerRef">
			<div class="scrollee">
				<div
					v-for="i in eventsInRanker"
					:key="i"
					class="rank mono"
					:class="{
						odd: i % 2 === 1,
						[rankedEvents[i - 1]?.event_type || 'mixed']: true,
						selected: rankedEvents[i - 1]?.id === eventStore.selectedEventId,
						hovering: rankedEvents[i - 1]?.id === eventStore.hoveringEvent?.id,
					}"
					@click="selectEvent(rankedEvents[i - 1] || null)"
					@mouseover="eventStore.setHoveringEvent(rankedEvents[i - 1] || null)"
					@mouseleave="eventStore.setHoveringEvent(null)"
					:title="`Duration: ${eventStore.durationForEvent(rankedEvents[i - 1])} days\nSize: ${eventStore.sizeForEvent(rankedEvents[i - 1]).toFixed(2)} km²\nIntensity: ${eventStore.intensityForEvent(rankedEvents[i - 1]).toFixed(2)}`"
				>
					{{ i }}
				</div>
				<div
					v-if="props.events.length > topN"
					class="rank mono"
					style="background-color: var(--panel-hint)"
					:class="{
						odd: topN % 2 === 1,
						[eventStore.selectedEvent?.event_type || 'mixed']: true,
					}"
				>
					...
				</div>
				<div
					v-if="
						props.events.length > topN &&
						eventStore.selectedEvent &&
						selectedIndex > topN
					"
					class="rank mono selected"
					:class="{
						odd: topN % 2 === 0,
						[eventStore.selectedEvent.event_type || 'mixed']: true,
						selected: selectFinal,
					}"
					@mouseover="
						eventStore.setHoveringEvent(
							eventStore.selectedEvent as any as ExtremeEvent,
						)
					"
					@mouseleave="eventStore.setHoveringEvent(null)"
					:title="
						eventStore.selectedEvent
							? `Duration: ${eventStore.durationForEvent(eventStore.selectedEvent)} days\nSize: ${eventStore.sizeForEvent(eventStore.selectedEvent).toFixed(2)} km²\nIntensity: ${eventStore.intensityForEvent(eventStore.selectedEvent).toFixed(2)}`
							: ''
					"
				>
					{{ selectedIndex }}
				</div>
				<svg
					width="100%"
					ref="eventRankerSvgRef"
					:height="
						ROW_SIZE *
						((selectedIndex < 0 || selectedIndex > props.topN) &&
						eventStore.selectedEvent
							? eventsInRanker + 2
							: eventsInRanker + 1)
					"
					preserveAspectRatio="none"
					style="pointer-events: none"
				>
					<defs>
						<filter id="rankedShadow" height="130%">
							<feDropShadow
								dx="1"
								dy="1"
								stdDeviation="2"
								flood-color="rgba(0, 0, 0, 0.5)"
							/>
						</filter>
					</defs>

					<transition-group name="ranked-event-list" tag="g">
						<rect
							v-for="(event, idx) in rankedEvents.slice(0, eventsInRanker)"
							class="ranked-event"
							:key="event.id"
							x="32"
							y="0"
							:transform="`translate(0, ${idx * ROW_SIZE + 0.5 * ROW_SIZE - 0.5 * heightScale(eventStore.sizeForEvent(event) || 0)})`"
							:width="widthScale(eventStore.durationForEvent(event) || 0)"
							:height="heightScale(eventStore.sizeForEvent(event) || 0)"
							:fill="eventStore.colorForEvent(event) || scssVars.c3sred"
							filter="url(#rankedShadow)"
						/>
						<rect
							v-if="
								eventsInRanker < props.events.length && eventStore.selectedEvent
							"
							class="ranked-event"
							x="32"
							y="0"
							:transform="`translate(0, ${(eventsInRanker + 1) * ROW_SIZE + 0.5 * ROW_SIZE - 0.5 * heightScale(eventStore.sizeForEvent(eventStore.selectedEvent) || 0)})`"
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
								eventStore.colorForEvent(
									eventStore.selectedEvent as any as ExtremeEvent,
								) || scssVars.c3sred
							"
						/>
					</transition-group>
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
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: flexstart;
			width: 100%;
			cursor: pointer;
			padding-left: 0.125rem;
			background-color: var(--panel-hint);
			&.odd {
				background-color: var(--panel-hint2);
			}

			&.hovering,
			&:hover {
				background-color: var(--highlight);
				box-shadow: 2px 2px 8px var(--primary-glass);
			}

			&.selected {
				border-top: 2px solid var(--highlight);
				border-bottom: 2px solid var(--highlight);
				box-shadow: 0 0 10px rgba(var(--primary), 0.5);
			}

			p {
				margin: 0;
				padding: 0 0.5rem;
			}
		}

		$rate: $animTime * 0.25;
		.ranked-event {
			position: relative;
			transition: transform $rate ease-out;
			
			rx: 2;
			// stroke: black;
			// stroke-width: 0.5;

			// Text styles
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
				fill: $c3spurple !important;
			}
		}
	}
}
</style>
