<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store/eventStore'
import { faClose } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { IconX } from '@tabler/icons-vue'

const eventStore = useStore()
const props = defineProps<{
	active: boolean
}>()
const emit = defineEmits(['close'])

const eventType = computed(
	() => eventStore.selectedEvent?.event_type || 'unknown',
)
</script>

<template>
	<div class="focus-frame" :class="{ active: props.active, [eventType]: true }">
	<button @click="emit('close')">
		<IconX size="16" aria-hidden="true" />
	</button>
		<!-- <div class="top-left"></div>
		<div class="top-right">
		</div>
		<div class="left"></div>
		<div class="right"></div>
		<div class="bottom"></div> -->
	</div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;
button {
	margin: 0;
	padding: 0;
	top: 0%;
	right: 0%;
	position: absolute;
	border: none;
	background-color: var(--primary-glass);
	backdrop-filter: $frosty;
	color: var(--text-on-primary);
	font-size: 1.2rem;
	border-radius: 0 0 0 0.5rem;
	cursor: pointer;
	svg {
		margin: 0;
		height: 100%;
		width: 100%;
	}
	&:hover {
		background-color: var(--primary-hover);
	}
	width: 2rem;
	height: 2rem;
	box-shadow: var(--shadow-sm), var(--shadow-md);
	pointer-events: auto;
}
.focus-frame {
	position: relative;
	// border: 2px dashed $c3sred;
	// pointer-events: none;
	width: 100%;
	height: 100%;
	z-index: 200;
	pointer-events: none; /* make parent not catch clicks */

	border: $panelMargin solid var(--primary-glass);
	box-shadow: inset 0 4px 12px rgba(0, 0, 0, 0.5);
	clip-path: polygon(
		0 0,
		calc(50% - $modeButtonWidth) 0,
		calc(50% - $modeButtonWidth) 3 * $panelMargin,
		calc(50% + $modeButtonWidth) 3 * $panelMargin,
		calc(50% + $modeButtonWidth) 0,
		100% 0,
		100% 100%,
		0 100%
	);

	> div {
		pointer-events: auto; /* children catch clicks */
		transition: all $animTime ease-in-out;
		box-shadow: var(--shadow-sm), var(--shadow-md);
	}

	transform: scale(1.5);
	&.active {
		transform: none;
	}
}
</style>
