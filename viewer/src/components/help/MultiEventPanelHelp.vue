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
			The Multi-Event Panel shows summary charts for all events currently displayed on the map.
			In Overview mode, open it using the
			<span class="button glassy color decoration">
				<IconChartBar class="icon" aria-hidden="true" />
			</span>
			button. If it is already open, it can be expanded to full screen with the maximise button.
		</p>
		<p>
			It consists of 3 charts which can be scrolled between.
		</p>
		<p>
			All charts plot the same variable, which can be selected using the buttons on the chart axes. Clicking the button will cycle through available variables:
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
		<p>
			The chart axis range can be controlled using the buttons at the bottom of the panel:
			<ul>
				<li><strong>Show most events</strong>: the axis is scaled to the 90th percentile range — most events will be visible, but very extreme outliers may fall outside the chart area.</li>
				<li><strong>Show all events</strong>: the axis covers the full range, including all outliers. This is the default.</li>
				<li><strong>Focus on selected event</strong>: the axis is scaled around the currently selected event.</li>
			</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
.icon {
	position: relative;
	top: 0.25rem;
}

</style>
