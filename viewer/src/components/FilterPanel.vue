<script setup lang="ts">
import { defineModel } from 'vue'
import { useLabels } from '@/lib/labels'
import {
	IconDimensions,
	IconFilter,
	IconMathEqualGreater,
	IconMathEqualLower,
	IconStopwatch,
	IconTemperature,
	IconTemperaturePlus,
	IconTemperatureMinus,
	IconRefreshAlert,
} from '@tabler/icons-vue'
import NumberSelect from './util/NumberSelect.vue'
import { useStore } from '@/store/store'

const store = useStore()

const $l = useLabels()

const model = defineModel<Filters>({ required: true })

const cycleHeatMode = async () => {
	await store.setLoading('Updating heat intensity filter...')
	if (model.value.heatIntensity.type === 'mean') {
		model.value.heatIntensity.type = 'max'
	} else if (model.value.heatIntensity.type === 'max') {
		model.value.heatIntensity.type = 'min'
	} else {
		model.value.heatIntensity.type = 'mean'
	}
	store.setLoadingDone()
}
const cycleColdMode = async () => {
	await store.setLoading('Updating cold intensity filter...')
	if (model.value.coldIntensity.type === 'mean') {
		model.value.coldIntensity.type = 'max'
	} else if (model.value.coldIntensity.type === 'max') {
		model.value.coldIntensity.type = 'min'
	} else {
		model.value.coldIntensity.type = 'mean'
	}
	store.setLoadingDone()
}

const resetDuration = async () => {
	await store.setLoading('Resetting duration filter...')
	model.value.duration.value = 3
	model.value.duration.minimum = true
	store.setLoadingDone()
}
const resetSize = async () => {
	await store.setLoading('Resetting size filter...')
	model.value.size.value = 0
	model.value.size.minimum = true
	store.setLoadingDone()	
}
const resetHeatIntensity = async () => {
	await store.setLoading('Resetting heat intensity filter...')
	model.value.heatIntensity.value = 28
	model.value.heatIntensity.minimum = true
	store.setLoadingDone()
}
const resetColdIntensity = async () => {
	await store.setLoading('Resetting cold intensity filter...')
	model.value.coldIntensity.value = 2
	model.value.coldIntensity.minimum = false
	store.setLoadingDone()
}
const toggleDurationLtGt = async () => {
	await store.setLoading('Updating duration filter...')
	model.value.duration.minimum = !model.value.duration.minimum
	store.setLoadingDone()
}
const toggleSizeLtGt = async () => {
	await store.setLoading('Updating size filter...')
	model.value.size.minimum = !model.value.size.minimum
	store.setLoadingDone()
}
const toggleHeatLtGt = async () => {
	await store.setLoading('Updating heat intensity filter...')
	model.value.heatIntensity.minimum = !model.value.heatIntensity.minimum
	store.setLoadingDone()
}
const toggleColdLtGt = async () => {
	await store.setLoading('Updating cold intensity filter...')
	model.value.coldIntensity.minimum = !model.value.coldIntensity.minimum
	store.setLoadingDone()
}
</script>

<template>
	<div class="filter-panel">
		<IconFilter class="header-icon" />

		<div class="filters">
			<div class="filter-row">
				<IconStopwatch />
				<button @click="toggleDurationLtGt" class="ltgt-button">
					<IconMathEqualGreater v-if="model.duration.minimum" />
					<IconMathEqualLower v-else />
				</button>
				<NumberSelect
					v-model="model.duration.value"
					:min="3"
					:max="14"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating duration filter...')"
					@loading-end="store.setLoadingDone()"
				/>
				<span class="units">days</span>
				<button
					@click="resetDuration"
					class="reset-button"
					:disabled="model.duration.value === 3"
				>
					<IconRefreshAlert />
				</button>
			</div>
			<div class="filter-row">
				<IconDimensions />
				<button
					@click="toggleSizeLtGt"
					class="ltgt-button"
				>
					<IconMathEqualGreater v-if="model.size.minimum" />
					<IconMathEqualLower v-else />
				</button>
				<NumberSelect
					v-model="model.size.value"
					:min="0"
					:max="1200"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating size filter...')"
					@loading-end="store.setLoadingDone()"
				/>
				<span class="units">km² </span>
				<button @click="resetSize" class="reset-button">
					<IconRefreshAlert />
				</button>
			</div>
			<div class="filter-row" v-if="model.heatIntensity.active">
				<button @click="cycleHeatMode">
					<IconTemperature
						v-if="model.heatIntensity.type === 'mean'"
						class="hot"
					/>
					<IconTemperaturePlus
						v-if="model.heatIntensity.type === 'max'"
						class="hot"
					/>
					<IconTemperatureMinus
						v-if="model.heatIntensity.type === 'min'"
						class="hot"
					/>
				</button>
				<button
					@click="toggleHeatLtGt"
					class="ltgt-button hot"
				>
					<IconMathEqualGreater v-if="model.heatIntensity.minimum" />
					<IconMathEqualLower v-else />
				</button>
				<NumberSelect
					v-model="model.heatIntensity.value"
					:min="0"
					:max="50"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating heat intensity filter...')"
					@loading-end="store.setLoadingDone()"
				/>
				<span class="units"> °C </span>
				<button @click="resetHeatIntensity" class="reset-button hot">
					<IconRefreshAlert />
				</button>
			</div>
			<div class="filter-row" v-if="model.coldIntensity.active">
				<button @click="cycleColdMode">
					<IconTemperature
						v-if="model.coldIntensity.type === 'mean'"
						class="cold"
					/>
					<IconTemperaturePlus
						v-if="model.coldIntensity.type === 'max'"
						class="cold"
					/>
					<IconTemperatureMinus
						v-if="model.coldIntensity.type === 'min'"
						class="cold"
					/>
				</button>
				<button
					@click="toggleColdLtGt"
					class="ltgt-button cold"
				>
					<IconMathEqualGreater v-if="model.coldIntensity.minimum" />
					<IconMathEqualLower v-else />
				</button>
				<NumberSelect
					v-model="model.coldIntensity.value"
					:min="-50"
					:max="2"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating cold intensity filter...')"
					@loading-end="store.setLoadingDone()"
				/>
				<span class="units"> °C </span>
				<button @click="resetColdIntensity" class="reset-button cold">
					<IconRefreshAlert />
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped lang="scss">
.filter-panel {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	font-family: sans-serif;
	background: var(--panel-bg);
	position: relative;
	padding: 1rem;
}

.header-icon {
	position: absolute;
	top: 0;
	left: 0;
	align-items: center;
	gap: 0.5rem;
	transform: translate(-25%, -25%);
	font-weight: bold;

	width: 1.5rem;
	height: 1.5rem;
	color: var(--text-tertiary);

	background: var(--panel-solid);
	border-radius: 50%;
	padding: 0.125rem;
}

.filters {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

.filter-row {
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
	gap: 0.25rem;

	.tabler-icon {
		flex: 1 0 1.5rem;
		width: 1.5rem;
		height: 1.5rem;
		color: var(--text-secondary);
	}
	.units {
		flex: 2 1 3rem;
		text-shadow: var(--text-on-primary-shadow);
	}

	button {
		flex: 1 1 1.5rem;
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		text-shadow: var(--text-on-primary-shadow);
		:disabled {
			color: red;
			background-color: aqua;
		}

		.tabler-icon {
			color: var(--primary);
		}

		.hot,
		&.hot {
			color: var(--theme-hot-primary);
		}
		.cold,
		&.cold {
			color: var(--theme-cold-primary);
		}
		&.reset-button {
			padding: 0 0 0.5rem 0.5rem;

			.tabler-icon {
				width: 1rem;
				height: 1rem;
			}
		}
	}

	.number-input {
		flex: 1 0 6rem;
	}
}

.label {
	font-weight: 500;
}
</style>
