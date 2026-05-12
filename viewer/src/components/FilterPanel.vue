<script setup lang="ts">
import { computed } from 'vue'
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
	IconCloudRain,
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
const resetWetIntensity = async () => {
	await store.setLoading('Resetting wet intensity filter...')
	model.value.wetIntensity.value = 0
	model.value.wetIntensity.minimum = true
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
const toggleWetLtGt = async () => {
	await store.setLoading('Updating wet intensity filter...')
	model.value.wetIntensity.minimum = !model.value.wetIntensity.minimum
	store.setLoadingDone()
}

// const durationTooltip = computed(() => {
// 	return `${$l.value.duration} ${model.value.duration.minimum ? $l.value.greaterThan : $l.value.lessThan} ${model.value.duration.value} days`
// })

// const sizeTooltip = computed(() => {
// 	return `${$l.value.size} ${model.value.size.minimum ? $l.value.greaterThan : $l.value.lessThan} ${model.value.size.value} km²`
// })

// const heatIntensityTooltip = computed(() => {
// 	return `${$l.value.intensity} ${
// 		model.value.heatIntensity.minimum ? $l.value.greaterThan : $l.value.lessThan
// 	} ${model.value.heatIntensity.value} °C`
// })

// const coldIntensityTooltip = computed(() => {
// 	return `${$l.value.intensity} ${
// 		model.value.coldIntensity.minimum ? $l.value.greaterThan : $l.value.lessThan
// 	} ${model.value.coldIntensity.value} °C`
// })

const sizeGetter = computed({
	get: () => model.value.size.value / 100_000,
	set: (val: number) => {
		store.setLoading('Updating size filter...')
		model.value.size.value = val * 100_000
		store.setLoadingDone()
	},
})
</script>

<template>
	<div class="filter-panel">
		<div class="filters">
			<div class="filter-row">
				<IconStopwatch v-tooltip.bottom="$l.duration" />
				<button
					@click="toggleDurationLtGt"
					class="ltgt-button"
					v-tooltip.bottom="
						model.duration.minimum
							? $l.switchTo + ' ' + $l.lessThan
							: $l.switchTo + ' ' + $l.greaterThan
					"
				>
					<IconMathEqualGreater
						v-if="model.duration.minimum"
						aria-hidden="true"
					/>
					<IconMathEqualLower v-else aria-hidden="true" />
				</button>
				<NumberSelect
					v-model="model.duration.value"
					:min="3"
					:max="14"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating duration filter...')"
					@loading-end="store.setLoadingDone()"
					v-tooltip.bottom="$l.durationNumberOfDays"
				/>
				<span class="units">days</span>
				<button
					@click="resetDuration"
					class="reset-button"
					:disabled="
						model.duration.value === 3 && model.duration.minimum === true
					"
					v-tooltip.bottom="$l.resetFilter"
				>
					<IconRefreshAlert aria-hidden="true" />
				</button>
			</div>
			<div class="filter-row">
				<IconDimensions v-tooltip.bottom="$l.size" />
				<button
					@click="toggleSizeLtGt"
					class="ltgt-button"
					v-tooltip.bottom="
						model.size.minimum
							? $l.switchTo + ' ' + $l.lessThan
							: $l.switchTo + ' ' + $l.greaterThan
					"
				>
					<IconMathEqualGreater v-if="model.size.minimum" aria-hidden="true" />
					<IconMathEqualLower v-else aria-hidden="true" />
				</button>
				<NumberSelect
					v-model="sizeGetter"
					:min="0"
					:max="100"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating size filter...')"
					@loading-end="store.setLoadingDone()"
					v-tooltip.bottom="$l.sizeNumberOfSquareKilometers"
				/>
				<span class="units">x100,000km²</span>
				<button
					@click="resetSize"
					:disabled="model.size.value === 0 && model.size.minimum === true"
					class="reset-button"
					v-tooltip.bottom="$l.resetFilter"
				>
					<IconRefreshAlert aria-hidden="true" />
				</button>
			</div>
			<div class="filter-row" v-if="model.heatIntensity.active">
				<IconTemperature
					class="hot"
					aria-hidden="true"
					v-tooltip.bottom="$l.intensity"
				/>
				<button
					@click="toggleHeatLtGt"
					class="ltgt-button hot"
					v-tooltip.bottom="
						model.heatIntensity.minimum
							? $l.switchTo + ' ' + $l.lessThan
							: $l.switchTo + ' ' + $l.greaterThan
					"
				>
					<IconMathEqualGreater
						v-if="model.heatIntensity.minimum"
						aria-hidden="true"
					/>
					<IconMathEqualLower v-else />
				</button>
				<NumberSelect
					v-model="model.heatIntensity.value"
					:min="28"
					:max="55"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating heat intensity filter...')"
					@loading-end="store.setLoadingDone()"
					v-tooltip.bottom="$l.intensityNumberOfDegrees"
				/>
				<span class="units"> °C </span>
				<button
					@click="resetHeatIntensity"
					class="reset-button hot"
					v-tooltip.bottom="$l.resetFilter"
					:disabled="
						model.heatIntensity.value === 28 &&
						model.heatIntensity.minimum === true
					"
				>
					<IconRefreshAlert aria-hidden="true" />
				</button>
			</div>
			<div class="filter-row" v-if="model.coldIntensity.active">
				<IconTemperature
					class="cold"
					aria-hidden="true"
					v-tooltip.bottom="$l.intensity"
				/>
				<button
					@click="toggleColdLtGt"
					class="ltgt-button cold"
					v-tooltip.bottom="
						model.coldIntensity.minimum
							? $l.switchTo + ' ' + $l.lessThan
							: $l.switchTo + ' ' + $l.greaterThan
					"
				>
					<IconMathEqualGreater
						v-if="model.coldIntensity.minimum"
						aria-hidden="true"
					/>
					<IconMathEqualLower v-else aria-hidden="true" />
				</button>
				<NumberSelect
					v-model="model.coldIntensity.value"
					:min="-50"
					:max="2"
					:step="1"
					class="number-input"
					@loading-start="store.setLoading('Updating cold intensity filter...')"
					@loading-end="store.setLoadingDone()"
					v-tooltip.bottom="$l.intensityNumberOfDegrees"
				/>
				<span class="units"> °C </span>
				<button
					@click="resetColdIntensity"
					class="reset-button cold"
					v-tooltip.bottom="$l.resetFilter"
					:disabled="
						model.coldIntensity.value === 2 &&
						model.coldIntensity.minimum === false
					"
				>
					<IconRefreshAlert aria-hidden="true" />
				</button>
			</div>
			<div class="filter-row" v-if="model.wetIntensity.active">
				<IconCloudRain
					aria-hidden="true"
					v-tooltip.bottom="$l.wetIntensityLabel"
				/>
				<button
					@click="toggleWetLtGt"
					class="ltgt-button"
					v-tooltip.bottom="
						model.wetIntensity.minimum
							? $l.switchTo + ' ' + $l.lessThan
							: $l.switchTo + ' ' + $l.greaterThan
					"
				>
					<IconMathEqualGreater
						v-if="model.wetIntensity.minimum"
						aria-hidden="true"
					/>
					<IconMathEqualLower v-else aria-hidden="true" />
				</button>
				<NumberSelect
					v-model="model.wetIntensity.value"
					:min="0"
					:max="10"
					:step="0.1"
					class="number-input"
					@loading-start="store.setLoading('Updating wet intensity filter...')"
					@loading-end="store.setLoadingDone()"
					v-tooltip.bottom="$l.wetIntensityLabel"
				/>
				<span class="units"> </span>
				<button
					@click="resetWetIntensity"
					class="reset-button"
					v-tooltip.bottom="$l.resetFilter"
					:disabled="
						model.wetIntensity.value === 0 &&
						model.wetIntensity.minimum === true
					"
				>
					<IconRefreshAlert aria-hidden="true" />
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
			&:disabled {
				opacity: 0.5;
				cursor: not-allowed;
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
