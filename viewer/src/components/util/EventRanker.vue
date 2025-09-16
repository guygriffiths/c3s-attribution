<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import scssVars from '@/assets/styles/scssVars.module.scss'
import * as d3 from 'd3'
import { onRegionEventsReady } from '@/lib/eventFiltering'
const store = useStore()
const eventStore = useEventStore()

const props = defineProps<{
	events: ExtremeEvent[] // The events to rank
	// The metric to rank by
	sortFunc: (a: ExtremeEvent, b: ExtremeEvent) => number
	topN: number
}>()
const eventRankerSvgRef = ref<SVGSVGElement | null>(null)
const scrollerRef = ref<HTMLDivElement | null>(null)
const width = ref(300)

watch(eventRankerSvgRef, (el) => {
	if (!el) return
	const ro = new ResizeObserver(([entry]) => {
		width.value = entry.contentRect.width > 40 ? entry.contentRect.width : 50
	})
	ro.observe(el)
})

const widthScale = computed(() => {
	// Find the max duration in the currently filtered events
	return d3
		.scaleLinear()
		.domain(eventStore.durationRange)
		.range([20, width.value - 40])
		.clamp(true)
})
const heightScale = computed(() => {
	// Find the max duration in the currently filtered events
	return d3
		.scaleLinear()
		.domain(eventStore.sizeRange)
		.range([2, 30])
		.clamp(true)
})

const rankedEvents = ref<ExtremeEvent[]>([])
watch(
	() => props.events,
	() => {
		rankedEvents.value = [...(props.events || [])].sort(props.sortFunc).splice(0, props.topN)
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
					:height="32 * eventsInRanker"
					preserveAspectRatio="none"
					style="pointer-events: none"
				>
					<transition-group
						tag="g"
						name="ranked-event-fx"
						moveClass="ranked-event-fx-move"
					>
						<rect
							v-for="(event, idx) in rankedEvents"
							class="ranked-event"
							:key="event.id"
							:x="0"
							:y="idx * 32 + 16 - 0.5 * heightScale(event.pixel_set.length)"
							:width="widthScale(event.duration)"
							:height="heightScale(event.pixel_set.length)"
							:fill="eventStore.colorForEvent(event) || scssVars.c3sred"
						/>
						<text
							v-for="(event, idx) in rankedEvents"
							:key="`text-${event.id}`"
							class="ranked-event"
							:x="widthScale(event.duration) + 8"
							:y="idx * 32 + 22"
							font-size="16"
							fill="black"
						>
							{{ idx + 1 }}
						</text>
					</transition-group>
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
			flex: 0 0 2rem;
			min-height: 2rem;
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

		$rate: $animTime;
		.ranked-event {
			// transition: transform 2s linear;
			position: relative;
			transition:
				transform $rate ease-out,
				opacity $rate ease-out;
		}

		/* Leave phase */
		.ranked-event-fx-leave-from {
			opacity: 1;
		}
		.ranked-event-fx-leave-active {
			transition: transform calc(0.5 * $rate) ease-in;
		}
		.ranked-event-fx-leave-to {
			// opacity: 0;
			opacity: 1;
			transform: translateX(-100%);
		}

		.ranked-event-fx-enter-from {
			opacity: 1;
			transform: translateX(-100%);
		}
		.ranked-event-fx-enter-active {
			transition: transform $rate ease-in-out calc(0.25 * $rate);
		}
		.ranked-event-fx-enter-to {
			opacity: 1;
			transform: translateX(0);
		}
	}
}
</style>
