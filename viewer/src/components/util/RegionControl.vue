<script lang="ts" setup>
import { nextTick, ref } from 'vue'
import { useStore } from '@/store/store'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import {
	faDrawPolygon,
	faTimes,
	faMapMarkerAlt,
	faClose,
	faBan,
} from '@fortawesome/free-solid-svg-icons'
import * as d3 from 'd3'
import { useLabels } from '@/lib/labels'
import scssModule from '@/assets/styles/scssVars.module.scss'

const store = useStore()
const $l = useLabels()

const sizes: [
	number,
	string,
	'wraf-01' | 'wraf-05' | 'wraf-2' | 'wraf-5' | 'wraf-10',
][] = [
	[0.1, 'XS', 'wraf-01'],
	[0.5, 'S', 'wraf-05'],
	[2, 'M', 'wraf-2'],
	[5, 'L', 'wraf-5'],
	[10, 'XL', 'wraf-10'],
]
const selectedSize = ref<number | null>(null)

const selectSize = async (idx: number | null) => {
	store.setLoading() // start loading immediately
	selectedSize.value = idx
	store.wrafLevel = idx === null ? 'none' : sizes[idx][2]
}

const selectPoint = () => {
	selectedSize.value = null
	store.wrafLevel = 'none'
	// stub for your point handling
	console.log('Point selection triggered')
}

const sizeScheme = d3.interpolateWarm
</script>

<template>
	<div class="region-control">
		<div class="label">
			<FontAwesomeIcon :icon="faDrawPolygon" />
			<!-- <span>{{ $l.selectByRegion}}</span> -->
		</div>

		<div>
			<button
				:style="{ backgroundColor: 'black', color: 'white' }"
				title="None"
				@click="selectSize(null)"
			>
				<FontAwesomeIcon :icon="faBan" />
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
				:style="{ backgroundColor: scssModule.c3sred, color: 'white' }"
				title="Point"
				@click="selectPoint"
			>
				<FontAwesomeIcon :icon="faMapMarkerAlt" />
			</button>
		</div>
	</div>
</template>

<style scoped>
.region-control {
	display: flex;
	flex-direction: column;
	gap: 0;
	position: relative;
	margin-top: 0.75rem;
	margin-left: 0.25rem;

	.label {
		font-weight: bolder;
		font-family: 'Raleway', sans-serif;
		font-size: 1rem;
		position: absolute;
		top: -0.75rem;
		left: -0.75rem;
		background-color: rgba(255, 255, 255, 0.9);
		border-radius: 100%;
		padding: 0 0.3rem;
		border: 1px solid rgba(0, 0, 0, 0.2);
	}

	button {
		margin: 0 0.05rem;
		font-family: 'Raleway', sans-serif;
		font-weight: bolder;
	}
}
</style>
