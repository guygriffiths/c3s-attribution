<script setup lang="ts">
import { setTheme } from '@/lib/utils'
import {
	IconSnowflake,
	IconSun,
	IconTemperature,
	IconTemperatureSnow,
	IconTemperatureSun,
} from '@tabler/icons-vue'
import { set } from 'date-fns';
import { ref } from 'vue'

const props = defineProps<{
	hot: boolean
	cold: boolean
}>()

const emits = defineEmits<{
	(e: 'update:hot', value: boolean): void
	(e: 'update:cold', value: boolean): void
}>()

const coldClicked = () => {
	emits('update:cold', true)
	emits('update:hot', false)
	setTheme('cold')
}

const hotClicked = () => {
	emits('update:hot', true)
	emits('update:cold', false)
	setTheme('hot')
}

const lastOnWasHot = ref(props.hot)
const bothClickedfromMiddle = () => {
	if (props.hot && props.cold) {
		// both on -> turn one off
		if (lastOnWasHot.value) {
			emits('update:hot', true)
			emits('update:cold', false)
			setTheme('hot')
		} else {
			emits('update:hot', false)
			emits('update:cold', true)
			setTheme('cold')
		}
	} else {
		// one or none on -> turn both on
		emits('update:hot', true)
		emits('update:cold', true)
		setTheme('hotcold')
	}
}
</script>

<template>
	<div class="toggle-container">
		<button
			class="left cold glassy"
			@click="coldClicked"
			:class="{ selected: props.cold && !props.hot }"
		>
			<IconTemperatureSnow class="icon left" />
		</button>
		<button
			class="middle glassy"
			@click="bothClickedfromMiddle"
			:class="{ selected: props.hot && props.cold }"
		>
			<IconSnowflake class="icon leftmerge" />
			<IconTemperature class="icon thin" />
			<IconSun class="icon rightmerge" />
		</button>
		<button
			class="right hot glassy"
			@click="hotClicked"
			:class="{ selected: props.hot && !props.cold }"
		>
			<IconTemperatureSun class="icon right" />
		</button>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

.toggle-container {
	position: relative;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 0;
	cursor: pointer;
	height: 2.5rem;
	// gap: 2px;

	button {
		border: none;
		cursor: pointer;
		padding: 0;
		flex: 1 1 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		width: 2rem;
		border-radius: 0;

		&.left {
			border-top-left-radius: $borderRadius;
			border-bottom-left-radius: $borderRadius;
		}
		&.right {
			border-top-right-radius: $borderRadius;
			border-bottom-right-radius: $borderRadius;
		}

		&.hot {
			background-color: var(--theme-hot-primary-glass);

			&:hover {
				background-color: var(--theme-hot-primary-glass-shine);
			}
			&.selected {
				background-color: var(--theme-hot-primary-glass-shine);
			}
		}
		&.cold {
			background-color: var(--theme-cold-primary-glass);
			&:hover {
				background-color: var(--theme-cold-primary-glass-shine);
			}
			&.selected {
				background-color: var(--theme-cold-primary-glass-shine);
			}
		}

		&.middle {
			width: 8rem;
			background: linear-gradient(
				to right,
				var(--theme-cold-primary-glass),
				var(--theme-cold-primary-glass) 10%,
				var(--theme-hot-primary-glass) 90%,
				var(--theme-hot-primary-glass)
			);

			&:hover {
				background: linear-gradient(
					to right,
					var(--theme-cold-primary-glass-shine),
					var(--theme-cold-primary-glass-shine) 10%,
					var(--theme-hot-primary-glass-shine) 90%,
					var(--theme-hot-primary-glass-shine)
				);
			}
			&.selected {
				background: linear-gradient(
					to right,
					var(--theme-cold-primary-glass-shine),
					var(--theme-cold-primary-glass-shine) 10%,
					var(--theme-hot-primary-glass-shine) 90%,
					var(--theme-hot-primary-glass-shine)
				);
			}
		}
	}

	.icon {
		color: white;
		font-size: 1rem;
		z-index: 2;

		&.thin {
			margin: -4px;
		}
		&.leftmerge {
			// clip-path: inset(0 20% 0 0); /* left half visible */
			transform: scale(0.9);
			transform: translateX(20%);
		}

		&.rightmerge {
			// clip-path: inset(0 0 0 20%); /* left half visible */
			transform: scale(0.9);
			transform: translateX(-20%);
		}
	}
}
</style>
