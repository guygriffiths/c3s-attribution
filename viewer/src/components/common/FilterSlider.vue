<script setup>
import { computed, watch, ref } from 'vue'

const props = defineProps({
	type: {
		type: String,
		required: true,
		validator: (t) => ['high-pass', 'low-pass', 'band-pass'].includes(t),
	},
	min: {
		type: Number,
		default: 0,
	},
	max: {
		type: Number,
		default: 100,
	},
})

const emit = defineEmits(['drag-start', 'drag-end'])

function handleStart() {
	emit('drag-start')
}
function handleEnd() {
	emit('drag-end')
}

const model = defineModel()

const isBand = computed(() => props.type === 'band-pass')

// Local reactive values
const lowVal = ref(props.min)
const highVal = ref(props.max)

watch(
	model,
	(v) => {
		if (isBand.value) {
			if (Array.isArray(v)) {
				lowVal.value = Math.min(Math.max(v[0], props.min), props.max)
				highVal.value = Math.min(Math.max(v[1], props.min), props.max)
				if (lowVal.value > highVal.value)
					[lowVal.value, highVal.value] = [highVal.value, lowVal.value]
			} else {
				lowVal.value = props.min
				highVal.value = props.max
			}
		} else {
			highVal.value = Math.min(Math.max(v ?? props.min, props.min), props.max)
		}
	},
	{ immediate: true },
)

function onLowInput(e) {
	let val = Number(e.target.value)
	val = Math.min(Math.max(val, props.min), highVal.value)
	lowVal.value = val
	model.value = [val, highVal.value]
}
function onHighInput(e) {
	let val = Number(e.target.value)
	val = Math.max(Math.min(val, props.max), lowVal.value)
	highVal.value = val
	model.value = [lowVal.value, val]
}
function onSingleInput(e) {
	let val = Number(e.target.value)
	val = Math.min(Math.max(val, props.min), props.max)
	model.value = val
}

// Compute percentages for gradients
const lowPct = computed(
	() => ((lowVal.value - props.min) / (props.max - props.min)) * 100,
)
const highPct = computed(
	() => ((highVal.value - props.min) / (props.max - props.min)) * 100,
)

// Background gradient for the track
const backgroundStyle = computed(() => {
	if (props.type === 'high-pass') {
		// Colour included from thumb to max (green), excluded before thumb (grey)
		return `linear-gradient(to right,
      #ddd 0%,
      #ddd ${highPct.value}%,
      #4caf50 ${highPct.value}%,
      #4caf50 100%)`
	} else if (props.type === 'low-pass') {
		// Included from min to thumb (green), excluded after (grey)
		return `linear-gradient(to right,
      #4caf50 0%,
      #4caf50 ${highPct.value}%,
      #ddd ${highPct.value}%,
      #ddd 100%)`
	} else if (props.type === 'band-pass') {
		// Included between lowPct and highPct, excluded outside
		return `linear-gradient(to right,
      #ddd 0%,
      #ddd ${lowPct.value}%,
      #4caf50 ${lowPct.value}%,
      #4caf50 ${highPct.value}%,
      #ddd ${highPct.value}%,
      #ddd 100%)`
	}
	return ''
})
</script>

<template>
	<div class="filter-slider">
		<template v-if="isBand">
			<div class="range">
				<label>Min:</label>
				<input
					type="range"
					:min="props.min"
					:max="props.max"
					:value="lowVal"
					@mousedown="handleStart"
					@touchstart="handleStart"
					@mouseup="handleEnd"
					@touchend="handleEnd"
					:style="{ background: backgroundStyle }"
				/>
				<span>{{ lowVal }}</span>
			</div>
			<div class="range">
				<label>Max:</label>
				<input
					type="range"
					:min="props.min"
					:max="props.max"
					:value="highVal"
					@change="onHighChange"
					@input="onHighInput"
					:style="{ background: backgroundStyle }"
				/>
				<span>{{ highVal }}</span>
			</div>
		</template>

		<template v-else>
			<div class="range">
				<input
					type="range"
					:min="props.min"
					:max="props.max"
					:value="highVal"
					@change="onSingleChange"
					@input="onSingleInput"
					:style="{ background: backgroundStyle }"
				/>
				<span>
					<template v-if="props.type === 'high-pass'">≥ {{ highVal }}</template>
					<template v-else-if="props.type === 'low-pass'"
						>≤ {{ highVal }}</template
					>
				</span>
			</div>
		</template>
	</div>
</template>

<style scoped>
.filter-slider {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.range {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	user-select: none;
}

input[type='range'] {
	flex: 1;
	-webkit-appearance: none;
	appearance: none;
	height: 6px;
	border-radius: 3px;
	background: #ddd;
	outline: none;
	cursor: pointer;
}

/* WebKit */
input[type='range']::-webkit-slider-thumb {
	-webkit-appearance: none;
	appearance: none;
	width: 16px;
	height: 16px;
	border-radius: 50%;
	background: #4caf50;
	cursor: pointer;
	margin-top: -5px;
	border: none;
	box-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

/* Firefox */
input[type='range']::-moz-range-thumb {
	width: 16px;
	height: 16px;
	border-radius: 50%;
	background: #4caf50;
	cursor: pointer;
	border: none;
	box-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}
</style>
