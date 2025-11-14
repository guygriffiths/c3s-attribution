<script setup lang="ts">
import { IconChevronUp, IconChevronDown } from '@tabler/icons-vue'
import { computed, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'

interface Props {
	min?: number
	max?: number
	step?: number
	label?: string
	hint?: string
	debounce?: number
}

const props = withDefaults(defineProps<Props>(), {
	min: 0,
	max: 100,
	step: 1,
	label: '',
	hint: '',
	debounce: 800,
})

const model = defineModel<number>({ required: true })
const localModel = ref(model.value)

const emit = defineEmits<{
	changeComplete: [value: number]
	loadingStart: []
	loadingEnd: []
}>()

const isLoading = ref(false)

const handleChangeComplete = async (value: number) => {
    // console.log('handleChangeComplete called with', value);
	// Wait for DOM updates and paint
	await new Promise((resolve) => requestAnimationFrame(resolve))
    // console.log('1st promise returned');
	await new Promise((resolve) => requestAnimationFrame(resolve))

    // console.log('setting value');
	model.value = value

	isLoading.value = false
	emit('loadingEnd')
    // console.log('emitted loadingEnd');
}

const debouncedChange = useDebounceFn(handleChangeComplete, 500) //props.debounce)

watch(localModel, (newValue) => {
    // console.log('model changed to (deboucne)', newValue);
	debouncedChange(newValue)
})

watch(
    model,
    (newValue) => {
        localModel.value = newValue
    }
)

const increment = () => {
	if (!isLoading.value) {
		isLoading.value = true
        // console.log('emitting loadingStart')
		emit('loadingStart')
	}
	const newValue = localModel.value + props.step
	if (newValue <= props.max) {
		localModel.value = newValue
	}
}

const decrement = () => {
	if (!isLoading.value) {
		isLoading.value = true
		emit('loadingStart')
	}
	const newValue = localModel.value - props.step
	if (newValue >= props.min) {
		localModel.value = newValue
	}
}

const validate = () => {
	if (model.value < props.min) model.value = props.min
	if (model.value > props.max) model.value = props.max
}

const canIncrement = computed(() => model.value < props.max)
const canDecrement = computed(() => model.value > props.min)
</script>

<template>
	<div class="number-selector">
		<label v-if="label" class="label">{{ label }}</label>
		<div class="input-wrapper">
			<input
				type="number"
				v-model.number="localModel"
				:min="min"
				:max="max"
				:step="step"
				:class="{ loading: isLoading }"
				@blur="validate"
			/>
			<div class="steppers">
				<button
					@click="increment"
					:disabled="!canIncrement"
					aria-label="Increase value"
					type="button"
				>
					<IconChevronUp :size="16" />
				</button>
				<button
					@click="decrement"
					:disabled="!canDecrement"
					aria-label="Decrease value"
					type="button"
				>
					<IconChevronDown :size="16" />
				</button>
			</div>
		</div>
		<span v-if="hint" class="hint">{{ hint }}</span>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.number-selector {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.label {
	font-size: 14px;
	font-weight: 500;
	color: var(--text-primary);
}

.input-wrapper {
	position: relative;
	display: flex;
	align-items: center;
}

input[type='number'] {
	width: 100%;
	background: rgba(0, 0, 0, 0.03);
	border: 1px solid var(--divider-subtle);
	border-radius: 6px;
	padding: 10px 40px 10px 14px;
	font-size: 17px;
	font-weight: 500;
	color: var(--text-primary);
	transition: all $transition;

	// Hide native steppers
	&::-webkit-inner-spin-button,
	&::-webkit-outer-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	-moz-appearance: textfield;

	&:hover {
		border-color: var(--divider);
		background: rgba(0, 0, 0, 0.05);
	}

	&:focus {
		outline: none;
		border-color: var(--primary);
		background: var(--panel-surface);
		box-shadow: 0 0 0 3px var(--focus-ring);
	}

	&.loading {
		cursor: progress;
	}
}

.steppers {
	position: absolute;
	right: 2px;
	top: 50%;
	transform: translateY(-50%);
	display: flex;
	flex-direction: column;
	gap: 2px;

	button {
		width: 26px;
		height: 20px;
		padding: 0;
		border: none;
		background: transparent;
		color: var(--text-secondary);
		border-radius: 3px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 150ms ease;

		&:hover:not(:disabled) {
			background: var(--hover-bg);
			color: var(--primary);
		}

		&:active:not(:disabled) {
			transform: scale(0.9);
		}

		&:disabled {
			opacity: 0.3;
			cursor: not-allowed;
		}
	}
}

.hint {
	font-size: 13px;
	color: var(--text-secondary);
}
</style>
