<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useStore } from '@/store/store'
import scssVars from '@/assets/styles/scssVars.module.scss'
import { svg } from 'd3'

const store = useStore()

const props = defineProps<{
	// The metric to rank by
	sortFunc: (a: ExtremeEvent, b: ExtremeEvent) => number
	topN: number
}>()

const rankedEvents = computed(() => {
	return store.selectedPointFilter
		? [...store.regionFilteredEvents].sort(props.sortFunc)
		: store.filters.wrafRegion
			? [...store.filteredEvents].sort(props.sortFunc)
			: []
})

// Grows as needed but doesn't ever shrink. Means we can end up in empty space.
// BUT...
// The obvious way of doing it means that the scroll boxes jitter when we get low numbers of events...

const nRanksToShow = ref(props.topN)
watch(rankedEvents, (newVal) => {
	nRanksToShow.value = Math.max(nRanksToShow.value, newVal.length)
})
</script>

<template>
	<div class="event-ranker">
		<div class="scroller">
			<div class="scrollee">
				<div
					v-for="i in nRanksToShow"
					:key="i"
					class="rank"
					:class="{ odd: i % 2 === 1 }"
				>
					<p>{{ i }}</p>
				</div>
				<svg
					width="100%"
					:height="32 * nRanksToShow"
					preserveAspectRatio="none"
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
							:y="idx * 32 + 8"
							:width="event.duration"
							height="16"
							:fill="event.color || scssVars.c3sred"
						/>
					</transition-group>
				</svg>
			</div>
		</div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.scroller {
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
			background-color: lightblue;
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: flex-end;
			width: 100%;

			&.odd {
				background-color: darken(lightblue, 5%);
			}

			p {
				margin: 0;
				padding: 0 0.5rem;
			}
		}
	}
}

$rate: $animTime;

.event-ranker {
	width: 100%;
	height: 100%;
	overflow: visible;

	svg {
		// background-color: white;
		border: 1px solid black;
		box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
	}

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
</style>
