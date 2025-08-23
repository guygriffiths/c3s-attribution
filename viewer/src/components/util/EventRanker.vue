<script setup lang="ts">
import { computed } from 'vue'
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
		: []//[...store.filteredEvents].sort(props.sortFunc)
})
</script>

<template>
	<div class="event-ranker">
		<svg width="100%" height="100%" :viewBox="`0 0 100 100`">
			<transition-group tag="g" name="ranked-event-fx" class="bars">
				<rect
					v-for="(event, idx) in rankedEvents"
                    class="ranked-event"
					:key="event.id"
					:x="0"
					:y="idx * 10 + 2.5"
					:width="event.duration"
					height="5"
					:fill="event.color || scssVars.c3sred"
				/>
			</transition-group>
		</svg>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.event-ranker {
	width: 100%;
	height: 100%;
    overflow: hidden;

    .ranked-event {
        transition: transform 2s ease-in-out;
    }

    .ranked-event-fx-enter-start {
        transform: translateX(100%);
    }
    .ranked-event-fx-enter-to {
        transform: translateX(0%);
    }

    .ranked-event-fx-leave-to {
        transform: translateY(100%);
    }
}
</style>
