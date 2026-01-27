<script setup lang="ts">
import {
	IconStopwatch,
	IconDimensions,
	IconTemperaturePlus,
	IconTemperatureMinus,
	IconChartBar,
	IconChartScatter,
	IconTimeline,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'

const eventStore = useEventStore()
</script>

<template>
	<div class="help-content">
		<p>
			This panel provides summary charts of all of the events currently plotted
			on the map. It consists of 3 charts which can be scrolled between.
		</p>
		<p>
			All charts will plot the same variable, which can be selected using the buttons on the chart axes. Clicking the button will cycle through available variables:
			<div class="icon-ul">
				<span class="icon-li">
					<IconStopwatch class="icon" aria-hidden="true" /> Event durations
				</span class="icon-li">
				<span class="icon-li">
					<IconDimensions class="icon" aria-hidden="true" /> Event sizes (total area covered, in km²)
				</span class="icon-li">
				<span class="icon-li" v-if="eventStore.eventTypeMode === 'hot'" >
					<IconTemperaturePlus class="icon" aria-hidden="true" /> Maximum temperature reached by a single grid cell within this event
				</span class="icon-li">
				<span class="icon-li" v-elif="eventStore.eventTypeMode === 'cold'" >
					<IconTemperatureMinus class="icon" aria-hidden="true" /> Minimum temperature reached by a single grid cell within this event
				</span class="icon-li">
				</div>
		</p>

		<p>
			<IconChartBar class="icon" aria-hidden="true" /> The first chart shows the
			distribution of plotted event values. 
		</p>
		<p>
			<IconChartScatter class="icon" aria-hidden="true" /> The second chart shows two parameters of the events plotted against each other. The X and Y axes can be changed by clicking on the axis labels.
		</p>
		<p>
			<IconTimeline class="icon" aria-hidden="true" /> The third chart shows how the selected variable changes over time for all events. The X axis is always time, and the range shown corresponds to the time range selected in the time selector.
		</p>

	</div>
</template>

<style lang="scss" scoped>
.icon {
	position: relative;
	top: 0.25rem;
}

.icon-ul {
	display: flex;
	flex-direction: column;
	padding-left: 1.5rem;

	.icon-li {
		display: flex;
		align-items: center;
		margin-bottom: 0.5rem;

		.icon {
			margin-right: 0.5rem;
		}
	}
}
</style>
