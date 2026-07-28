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
		<p>This panel provides detailed information about the currently selected day of the currently selected event. It features:
		<ul>
			<li>A histogram showing the temperature distribution for the selected day.</li>
			<li>The selected date being displayed.</li>
			<li>The most extreme temperature for the selected day.</li>
			<li>The average of the temperatures for the selected day.</li>
			<li>The area, in km², affected by the event on the selected day.</li>
		</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
</style>
