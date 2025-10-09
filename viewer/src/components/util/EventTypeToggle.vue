<script setup lang="ts">
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faGauge,
	faCalendarDays,
	faTemperatureHigh,
	faTemperatureLow,
	faPlus,
	faCertificate,
	faSnowflake,
	faBolt,
} from '@fortawesome/free-solid-svg-icons'
import { nextTick, ref, watch } from 'vue'
import { useStore } from '@/store/store'

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
}

const hotClicked = () => {
	emits('update:hot', true)
	emits('update:cold', false)
}

const lastOnWasHot = ref(props.hot)
const bothClickedfromMiddle = () => {
	if (props.hot && props.cold) {
		// both on -> turn one off
		if (lastOnWasHot.value) {
			emits('update:hot', true)
			emits('update:cold', false)
		} else {
			emits('update:hot', false)
			emits('update:cold', true)
		}
	} else {
		// one or none on -> turn both on
		emits('update:hot', true)
		emits('update:cold', true)
	}
}
</script>

<template>
	<div class="toggle-container">
		<button
			class="left cold"
			@click="coldClicked"
			:class="{ selected: props.cold && !props.hot }"
		>
			<FontAwesomeIcon :icon="faSnowflake" class="icon" />
		</button>
		<button
			class="middle"
			@click="bothClickedfromMiddle"
			:class="{ selected: props.hot && props.cold }"
		>
			<FontAwesomeIcon :icon="faSnowflake" class="icon leftmerge" />
			<FontAwesomeIcon :icon="faBolt" class="icon thin" />
			<FontAwesomeIcon :icon="faTemperatureHigh" class="icon rightmerge" />
			<!-- <FontAwesomeIcon :icon="faCertificate" class="icon right" /> -->
		</button>
		<button
			class="right hot"
			@click="hotClicked"
			:class="{ selected: props.hot && !props.cold }"
		>
			<FontAwesomeIcon :icon="faTemperatureHigh" class="icon right" />
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
	width: 8rem;
	height: 2.5rem;
	// gap: 2px;

	button {
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		margin: 0;
		// width: 33.33%;
		// height: 100%;
		flex: 1 1 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		transition:
			background-color 0.3s ease,
			color 0.3s ease;
		border-radius: 0;
		// width: 2rem;
		height: 100%;

		&.left {
			// border-top-left-radius: 0.5rem;
			border-bottom-left-radius: 0.5rem;
			border-right: 1px solid transparent;
		}
		&.right {
			// border-top-right-radius: 0.5rem;
			border-bottom-right-radius: 0.5rem;
			border-left: 1px solid transparent;
		}

		&.hot {
			background-color: $c3sred;
			border-color: color.adjust($c3sred, $lightness: -10%);
		}
		&.cold {
			background-color: $c3sblue;
			border-color: color.adjust($c3sblue, $lightness: -10%);
		}

		&.middle {
			background: linear-gradient(
				to right,
				$c3sblue,
				$c3sblue 10%,
				$c3sred 90%,
				$c3sred
			);
			border-left: 1px solid color.adjust($c3sblue, $lightness: -10%);
			border-right: 1px solid color.adjust($c3sred, $lightness: -10%);
		}

		&.selected {
			color: white;
			// transform: translate(1px,1px);
			&.hot {
				background-color: color.adjust($c3sred, $lightness: 10%);
			}
			&.cold {
				background-color: color.adjust($c3sblue, $lightness: 10%);
				border-right-color: color.adjust($c3sblue, $lightness: 20%);
			}
			&.middle {
				background: linear-gradient(
					to right,
					color.adjust($c3sblue, $lightness: 10%),
					color.adjust($c3sblue, $lightness: 10%) 10%,
					color.adjust($c3sred, $lightness: 10%) 90%,
					color.adjust($c3sred, $lightness: 10%)
				);
				border-left-color: color.adjust($c3sblue, $lightness: 20%);
				border-right-color: color.adjust($c3sred, $lightness: 20%);
			}
			box-shadow: 0 0 6px rgba(0, 0, 0, 0.2);
		}
	}

	.icon {
		color: white;
		font-size: 1rem;
		z-index: 2;

		&.thin {
			transform: scale(0.5,1.5);
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
