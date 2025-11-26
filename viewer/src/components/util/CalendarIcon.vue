<script setup>
import * as Tabler from '@tabler/icons-vue'
import { computed, useAttrs } from 'vue'

const props = defineProps({
	date: { type: Number, required: false },
	size: { type: [Number, String], default: 24 },
})

const validDate = computed(() => {
	return props.date && props.date >= 1 && props.date <= 31
})

const Comp = computed(() => {
	if (!validDate.value) {
		return Tabler.IconGripHorizontal
	}
	return Tabler[`IconNumber${props.date}Small`]
})

const attrs = useAttrs()
</script>

<template>
	<div class="wrapper">
		<Tabler.IconCalendar :size="props.size" class="calendar-frame" />
		<component
			:is="Comp"
			v-bind="attrs"
			class="date-text"
			:size="Math.ceil(props.size * 0.75)"
			:name="`Number${date}Small`"
			:style="{
				left: `${props.size * 0.5}px`,
				transform: validDate
					? 'translate(-50%, 37.5%)'
					: `translate(-50%, 37.5%) scale(0.7)`,
			}"
		/>
	</div>
</template>

<style>
.wrapper {
	position: relative;
	display: block;
}

.calendar-frame {
	/* Remove the inner details of the calendar icon to make space for the date number */
	:deep(.calendar-frame > path:nth-child(4)),
	:deep(.calendar-frame > path:nth-child(5)),
	:deep(.calendar-frame > path:nth-child(6)) {
		display: none !important;
		opacity: 0 !important;
	}
}

.date-text {
	/* Position the icon in the calendar icon */
	position: absolute;
}
</style>
