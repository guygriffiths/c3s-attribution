<script setup lang="ts">
import {
	IconStopwatch,
	IconDimensions,
	IconTemperature,
	IconSortDescendingSmallBig,
	IconSortAscendingSmallBig,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'

const store = useStore()
</script>

<template>
	<div class="help-content">
		<p>This panel provides contextual time series graphs for the currently selected event.
		<ul>
			<li>A line graph showing the most extreme temperature for each day of the event.</li>
			<li>A bar chart showing the total area affected on each day of the event.</li>
		</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
</style>
