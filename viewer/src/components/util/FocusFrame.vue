<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store/store'
import { faClose } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

const store = useStore()
const props = defineProps<{
	active: boolean
}>()
const emit = defineEmits(['close'])
</script>

<template>
	<div class="focus-frame" :class="{ active: props.active }">
		<div class="top">
			<button @click="emit('close')">
				<FontAwesomeIcon :icon="faClose" />
			</button>
		</div>
		<div class="left"></div>
		<div class="right"></div>
		<div class="bottom"></div>
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;
.focus-frame {
	position: absolute;
	// border: 2px dashed $c3sred;
	// pointer-events: none;
	width: 100%;
	height: 100%;
	z-index: 20;
	pointer-events: none; /* make parent not catch clicks */

	> div {
		pointer-events: auto; /* children catch clicks */
		transition: all $animTime ease-in-out;
		box-shadow: calc(0.25 * $panelMargin) calc(0.25 * $panelMargin) calc(0.25 * $panelMargin)
			rgba(0, 0, 0, 0.5), 
            calc(0.5 * $panelMargin) calc(0.5 * $panelMargin) calc(0.5 * $panelMargin)
                rgba(0, 0, 0, 0.2);
	}

	.top,
	.bottom,
	.left,
	.right {
		position: absolute;
		background-color: $c3sred;
	}

	.top,
	.bottom {
		left: $panelMargin;
		width: calc(100% - $panelMargin);
		height: $panelMargin;
		z-index: 1;
	}

	.top {
		transform: translateY(calc(-2 * $panelMargin));
		top: 0;
		display: flex;
		justify-content: flex-end;
		button {
			margin: 0;
			padding: 0;
			border: none;
			background-color: $c3sred;
			color: white;
			font-size: 1.2rem;
			border-radius: 0 0 0 0.5rem;
			cursor: pointer;
			svg {
				margin: 0;
				height: 100%;
				width: 100%;
			}
			&:hover {
				background-color: $c3sred;
			}
			width: calc(2 * $panelMargin);
			height: calc(2 * $panelMargin);
					box-shadow: calc(0.25 * $panelMargin) calc(0.25 * $panelMargin) calc(0.25 * $panelMargin)
			rgba(0, 0, 0, 0.5), 
            calc(0.5 * $panelMargin) calc(0.5 * $panelMargin) calc(0.5 * $panelMargin)
                rgba(0, 0, 0, 0.2);
		}
	}

	.bottom {
		transform: translateY(calc(2 * $panelMargin));
		bottom: 0;
	}

	.left,
	.right {
		top: 0;
		width: $panelMargin;
		height: 100%;
		z-index: 0;
	}

	.left {
		transform: translateX(calc(-2 * $panelMargin));
		left: 0;
	}

	.right {
		transform: translateX(calc(2 * $panelMargin));
		top: calc(2 * $panelMargin);
		right: 0;
		z-index: 10;
	}

	&.active {
		div {
			transform: none;
		}
	}
}
</style>
