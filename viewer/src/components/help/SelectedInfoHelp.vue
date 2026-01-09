<script setup lang="ts">
import {
	IconStopwatch,
	IconDimensions,
	IconReport,
	IconTemperaturePlus,
	IconTemperatureMinus,
	IconDownload,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'

const store = useStore()
</script>

<template>
	<div class="help-content">
		<p>This panel provides detailed information about the currently selected event.
			<ul>
				<li>The event's start and end dates.</li>
				<li><span class="icon"><IconStopwatch aria-hidden="true" /></span> The event's duration in whole days, including both the start and end days</li>
				<li><span class="icon"><IconDimensions aria-hidden="true" /></span> The total area covered by this event in square kilometres, over all days</li>
				<li><span class="icon"><IconTemperaturePlus aria-hidden="true" /></span>/<span class="icon"><IconTemperatureMinus aria-hidden="true" /></span> The event's extreme in °C. This is the highest/lowest temperature reached by any single grid cell during the event.</li>
				<li><span class="icon"><IconReport aria-hidden="true" /></span> <em>Coming Spring 2026 - relevant climate attribution information</em></li>
			</ul>
		</p>
		<p><span class="button glassy color decoration">
			<IconDownload aria-hidden="true" />
		</span> Download the raw event data as a JSON file for further analysis.</p>
	</div>
</template>

<style lang="scss" scoped>
.icon {
	position: relative;
	top: 0.25rem;
}
</style>
