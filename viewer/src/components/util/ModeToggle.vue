<script setup lang="ts">
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faGauge, faCalendarDays } from '@fortawesome/free-solid-svg-icons'
import { nextTick, watch } from 'vue'
import { useStore } from '@/store/store'

const mode = defineModel<'explore' | 'heatmap'>({ required: true })

const store = useStore()

const toggle = async () => {
	store.setLoading() // start loading immediately
  // Wait for the DOM update and rendering to complete
  await new Promise((resolve) => setTimeout(resolve, 0))
	mode.value = mode.value === 'explore' ? 'heatmap' : 'explore'
  store.setLoadingDone() // end loading after DOM updates
}
</script>

<template>
	<div class="switch" :class="mode" @click="toggle">
		<FontAwesomeIcon :icon="faGauge" class="icon left" />
		<div class="thumb"></div>
		<FontAwesomeIcon :icon="faCalendarDays" class="icon right" />
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.switch {
	position: relative;
	width: 80px;
	height: 36px;
	background-color: #ddd;
	border-radius: 9999px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0 10px;
	cursor: pointer;
	transition: background-color 0.3s ease;

	&.explore {
		background-color: $c3sblue;
	}

	&.heatmap {
		background-color: $c3sred;
	}

	.icon {
		color: white;
		font-size: 1rem;
		z-index: 2;

		&.left {
			margin-right: auto;
		}

		&.right {
			margin-left: auto;
		}
	}

	.thumb {
		position: absolute;
		top: 4px;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: white;
		transition: left 0.3s ease;
	}

	&.explore .thumb {
		left: 4px;
	}

	&.heatmap .thumb {
		left: calc(100% - 32px);
	}
}
</style>
