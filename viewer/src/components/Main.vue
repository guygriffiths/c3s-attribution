<script setup lang="ts">
import { onMounted, Ref, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import Map from './Map.vue'
import TimeReel from './TimeReel.vue'

const $l = useLabels()
const store = useStore()

onMounted(async () => {
})

const timePanelState: Ref<'min' | 'mid' | 'max'> = ref('min')
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

		<!-- <div id="buttons-debug">
			<button @click="console.log('clicky')">Click</button>
		</div>

		<div id="map"></div>
		<div id="times"></div>
		<div id="event"></div> -->
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.scss' as *;

.main {
	display: flex;
	flex-direction: column;

	#buttons-debug {
		position: absolute;
		left: 0;
		bottom: 0;
	}

	#map {
		flex: 1 1 100%;
		background-color: red;
	}
	
	#times {
		flex-grow: 0;
		flex-shrink: 0;
		background-color: yellow;
	}
	
	#event {
		flex-grow: 0;
		flex-shrink: 0;
		background-color: chartreuse;
	}
}
</style>
