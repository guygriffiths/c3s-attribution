<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import Map from './Map.vue'
import TimeReel from './common/TimeReel.vue'

const $l = useLabels()
const store = useStore()

onMounted(async () => {
})

const selTime = ref(new Date('2013-10-01T00:00:00Z'))
</script>

<template>
	<div class="main">
		<Map id="map"></Map>
		<TimeReel
			id="times"
			:start="store.startTime"
			:end="store.endTime"
			:events="store.events"
			v-model="store.selectedTime"
		></TimeReel>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.scss' as *;

.main {
	display: flex;
	flex-direction: column;

	#map {
		flex: 1 1 100%;
	}

	#times {
		flex-grow: 0;
		flex-shrink: 0;
	}
}
</style>
