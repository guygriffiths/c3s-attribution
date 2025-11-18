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
@use '@/assets/styles/scssVars.module.scss' as *;

.panel {
	position: absolute;
	transition:
		transform $transition,
		left $transition,
		right $transition,
		bottom $transition;
	z-index: 10;
}
.panel.left {
	transform: translateX(-150%);
}
.panel.right {
	transform: translateX(105%);
}
.panel.bottom {
	transform: translateY(150%);
}
.panel.top {
	transform: translateY(-150%);
}

.panel.left.peek {
	transform: translateX(-95%);
}
.panel.right.peek {
	transform: translateX(95%);
}
.panel.bottom.peek {
	transform: translateY(95%);
}
.panel.top.peek {
	transform: translateY(-95%);
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
