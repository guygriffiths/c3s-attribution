<script lang="ts" setup>
import { ref } from 'vue'
import { useStore } from '@/store/store'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faDrawPolygon, faTimes } from '@fortawesome/free-solid-svg-icons'
import * as d3 from 'd3'

const store = useStore()

const expanded = ref(false)
const sizes: [number, string, 'wraf-01' | 'wraf-05' | 'wraf-2' | 'wraf-5' | 'wraf-10'][] = [
	[0.1, 'XS', 'wraf-01'],
	[0.5, 'S', 'wraf-05'],
	[2, 'M', 'wraf-2'],
	[5, 'L', 'wraf-5'],
	[10, 'XL', 'wraf-10'],
]
const selectedSize = ref<number | null>(null) 

const toggleExpanded = () => (expanded.value = !expanded.value)
const selectSize = (idx: number | null) => {
	selectedSize.value = idx
	store.wrafLevel = idx === null ? 'none' : sizes[idx][2]
	expanded.value = false
}
const selectNone = () => {
	selectedSize.value = null
	store.wrafLevel = 'none'
	expanded.value = false
}
const sizeScheme = d3.interpolateWarm
</script>

<template>
	<div class="region-control">
		<button
			v-if="!expanded"
			class="w-8 h-8 flex items-center justify-center rounded bg-white shadow hover:bg-gray-100"
			@click="toggleExpanded"
			title="Select region size"
			:style="{ backgroundColor: selectedSize !== null ? sizeScheme(selectedSize / 5) : undefined }"
		>
			<FontAwesomeIcon
				v-if="!store.wrafLevel || store.wrafLevel === 'none' || selectedSize === null"
				:icon="faDrawPolygon"
				class="text-gray-700"
			/>
			<span v-else>
				{{ sizes[selectedSize][1] }}
			</span>
		</button>

		<div v-else>
			<button
				@click="expanded = false"
				title="Close"
			>
				<FontAwesomeIcon :icon="faTimes" class="text-gray-700" />
			</button>
			<template v-for="(size, i) in sizes" :key="size">
				<button
					:style="{ backgroundColor: sizeScheme(i / 5) }"

					:title="`${size[0]} Mm²`"
					@click="selectSize(i)"
				>
					{{ size[1] }}
				</button>
			</template>
				<button
					:style="{ backgroundColor: 'black', color: 'white' }"
					title="None"
					@click="selectSize(null)"
				>
					None
				</button>
		</div>
	</div>
</template>

<style scoped>
.region-control {
	display: flex;
	flex-direction: column;
	gap: 0;
	button {
		margin: 0 0.05rem;
		font-family: 'Raleway', sans-serif;
		font-weight: bolder;
	}
}
</style>
