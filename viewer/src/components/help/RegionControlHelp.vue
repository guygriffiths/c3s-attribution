<script setup lang="ts">
import {
	IconLayersSelected,
	IconMapPin,
	IconPolygon,
	IconWorld,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'

const store = useStore()
</script>

<template>
	<div class="help-content">
		<p>
			Here you can choose how to filter the data geographically. The available
			options are:
		</p>
		<div class="icon-ul">
			<span class="icon-li">
				<IconWorld class="icon" aria-hidden="true" /> <p><b>Global</b>: No geographic filtering, all
			data is shown.</p>
			</span class="icon-li">
			<span class="icon-li">
				<IconPolygon class="icon" aria-hidden="true" /><p><b>Region selection</b>: Draw a polygon on the map to select a region.
			Events that intersect that region will be shown.</p>
			</span class="icon-li">
			<span class="icon-li">
				<IconMapPin class="icon" aria-hidden="true" /><p> <b>Point selection</b>: Click on the map to select a single point. Only
			events which have data for the grid cell containing that point will be shown.</p>
			</span class="icon-li">
		</div>
	</div>
</template>

<style lang="scss" scoped>

</style>
