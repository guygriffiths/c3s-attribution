<script setup lang="ts">
import { useStore } from '@/store/store'
import Panel from './util/Panel.vue'
import { watch, ref } from 'vue'
import { bbox } from '@turf/turf'
import { useLabels } from '@/lib/labels'
import { faClose } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

const store = useStore()
const $l = useLabels()

const emits = defineEmits<{
	(close: 'close'): void
}>()

const peepholeRef = ref<HTMLElement | null>(null)

// TODO Perhaps make this frame (all frames) actually fill the screen, but have a thin border
// DO it for all of them and then this panel is just the top part of the charts thing (we'll put the summary info there too, then an event gets the whole LHS
// It'll give focus wothout taking too mich real estate. It's all centralised too for the region panel, which is going to be a bit more complex


watch(peepholeRef, (newVal) => {
	if (newVal) {
		store.mapPeephole = newVal
	}
})
</script>
<template>
	<Panel class="region-panel">
		<div class="top frame">
			<button
				@click="emits('close')"
				class="close-button"
				:title="$l.closeRegionPanel"
			>
				<FontAwesomeIcon :icon="faClose" />
			</button>
		</div>
		<div class="left frame"></div>
		<div class="right frame"></div>
		<div ref="peepholeRef" class="peephole"></div>
		<div class="bottom-panel frame">
			<!-- Add region-specific content here -->
		</div>
	</Panel>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.region-panel {
	display: grid;
	grid-template-rows: $frameBorderWidth 50% 1fr;
	grid-template-columns: $frameBorderWidth 1fr $frameBorderWidth;
	grid-template-areas:
		'top top top'
		'left peephole right'
		'bottom bottom bottom';
	background-color: rgba(255, 255, 255, 0.1);
	pointer-events: none;

	.top.frame {
		grid-area: top;
		box-shadow: rgba(0, 0, 0, 0.5) 3px 3px 3px 0px;
		display: flex;
		flex-direction: row-reverse;
		border-top-right-radius: $frameBorderRadius;
		border-top-left-radius: 0;

		.close-button {
			margin: 0;
			padding: 0.125rem;
			border-radius: 0.125rem;
			width: $frameBorderWidth;
			height: $frameBorderWidth;
			background: none;
			color: $c3sred;
			&:hover {
				background-color: rgba($c3sred, 0.8);
				color: white;
			}
		}
	}
	.right.frame {
		grid-area: right;
	}
	.left.frame {
		grid-area: left;
		box-shadow: rgba(0, 0, 0, 0.5) 3px 3px 3px 0px;
	}
	.peephole {
        grid-area: peephole;
		pointer-events: none;
		background-color: transparent;
	}
    
	.frame {
        pointer-events: all;
		background-color: $panelBg;
		width: 100%;
		height: 100%;
	}
	.bottom-panel {
        grid-area: bottom;
        border-bottom-right-radius: $frameBorderRadius;
        border-bottom-left-radius: 0;
		padding: $frameBorderWidth;
	}
}
</style>
