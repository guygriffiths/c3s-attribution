<script setup lang="ts">
import { setTheme } from '@/lib/utils'
import {
	IconSnowflake,
	IconSun,
	IconTemperature,
	IconTemperatureSnow,
	IconTemperatureSun,
} from '@tabler/icons-vue'
import { nextTick, ref } from 'vue'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
const store = useStore()
const eventStore = useEventStore()
const model = defineModel({
	type: String as () => 'hotcold' | 'hot' | 'cold',
})

const coldClicked = async () => {
	await store.setLoading('Loading coldwave events...')
	model.value = 'cold'
	setTheme('cold')
	store.hamburgerMenuOpen = false
	eventStore.filters.coldIntensity.active = true
	eventStore.filters.heatIntensity.active = false
	await store.setLoadingDone()
}

const hotClicked = async () => {
	await store.setLoading('Loading heatwave events...')
	model.value = 'hot'
	setTheme('hot')
	store.hamburgerMenuOpen = false
	eventStore.filters.heatIntensity.active = true
	eventStore.filters.coldIntensity.active = false
	await store.setLoadingDone()
}

const bothClickedfromMiddle = async () => {
	await store.setLoading('Loading all temperature events...')
	model.value = 'hotcold'
	setTheme('hotcold')
	store.hamburgerMenuOpen = false
	eventStore.filters.heatIntensity.active = true
	eventStore.filters.coldIntensity.active = true
	await store.setLoadingDone()
}
</script>

<template>
	<div class="toggle-container">
		<button
			class="left cold glassy"
			@click="coldClicked"
			:class="{ selected: model === 'cold' }"
		>
			<IconTemperatureSnow class="icon left" />
		</button>
		<button
			class="middle glassy"
			@click="bothClickedfromMiddle"
			:class="{ selected: model === 'hotcold' }"
		>
			<IconSnowflake class="icon leftmerge" />
			<IconTemperature class="icon thin" />
			<IconSun class="icon rightmerge" />
		</button>
		<button
			class="right hot glassy"
			@click="hotClicked"
			:class="{ selected: model === 'hot' }"
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
		box-shadow: none;

		&.left {
			border-top-left-radius: $borderRadius;
			border-bottom-left-radius: $borderRadius;
		}
		&.right {
			border-top-right-radius: $borderRadius;
			border-bottom-right-radius: $borderRadius;
		}

		&.hot {
			background: var(--theme-hot-primary-glass);

			&:hover {
				background: var(--theme-hot-primary-glass-shine);
			}
			&.selected {
				background: var(--theme-hot-primary-glass-shine);
			}
			&:active {
				background: var(--theme-hot-primary-glass-dark);
			}
		}
		&.cold {
			background: var(--theme-cold-primary-glass);
			&:hover {
				background: var(--theme-cold-primary-glass-shine);
			}
			&.selected {
				background: var(--theme-cold-primary-glass-shine);
			}
			&:active {
				background: var(--theme-cold-primary-glass-dark);
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
			&:active {
				background: linear-gradient(
					to right,
					var(--theme-cold-primary-glass-dark),
					var(--theme-cold-primary-glass-dark) 10%,
					var(--theme-hot-primary-glass-dark) 90%,
					var(--theme-hot-primary-glass-dark)
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
