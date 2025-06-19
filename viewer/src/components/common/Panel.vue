<script setup>
import { computed } from 'vue'

const props = defineProps({
	active: Boolean,
	style: Object,
})

const classes = computed(() => ['panel', { active: props.active }])
</script>

<template>
	<div :class="classes" :style="style" v-bind="$attrs">
		<slot />
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.scss' as *;

.panel {
	display: flex;
  flex-direction: column;
	border-radius: 6px;
	justify-content: center;
	align-items: center;
	box-shadow: rgba(0, 0, 0, 0.5) 3px 3px 3px 0px;
	background-color: $panelBg;
	position: absolute;
	transition:
		transform $animTime ease,
		left $animTime ease,
		right $animTime ease,
		bottom $animTime ease;
	z-index: 10;
}

.panel.left {
	transform: translateX(-150%);
}
.panel.right {
	transform: translateX(150%);
}
.panel.bottom {
	transform: translateY(150%);
}
.panel.top {
	transform: translateY(-150%);
}

.panel.left.peek {
	transform: translateX(-100%);
}
.panel.right.peek {
	transform: translateX(100%);
}
.panel.bottom.peek {
	transform: translateY(100%);
}
.panel.top.peek {
	transform: translateY(-100%);
}

.panel.active.left {
	transform: translateX(0);
}
.panel.active.right {
	transform: translateX(0);
}
.panel.active.bottom {
	transform: translateY(0);
}
.panel.active.top {
	transform: translateY(0);
}

/* You can add more like .top, .bottom, etc. if needed */
</style>
