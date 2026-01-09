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
		<p>This menu provides access to various filters and settings which affect all events:
		<ul>
			<li>The type of events being displayed (hot, cold, or both).</li>
			<li>Several parameter filters which affect which events are shown.</li>
			<li>Access to further information about the tool.
			</li>
		</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
</style>
