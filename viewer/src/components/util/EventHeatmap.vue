<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

defineProps({
	// coords: { x, y, z } — tile coords from LGridLayer
	coords: Object,
})

const canvas = ref(null)

// Fake data accessor: given lon/lat, return pixel value (0–1)
function getPixelValue(lat, lon) {
	// Replace this with real lookup
	return Math.max(0, Math.min(1, Math.sin(lat * 0.1) * Math.cos(lon * 0.1)))
}

// Turn 0–1 to rgba
function getColor(val) {
	const r = Math.floor(255 * val)
	const g = 0
	const b = Math.floor(255 * (1 - val))
	return `rgba(${r},${g},${b},0.8)`
}

function drawTile() {
	const ctx = canvas.value.getContext('2d')
	const res = 16 // pixels per tile dimension — keep low for perf
	const step = props.size / res

	const tileBounds = getTileLatLonBounds(
		props.coords.x,
		props.coords.y,
		props.coords.z,
	)

	for (let i = 0; i < res; i++) {
		for (let j = 0; j < res; j++) {
			const lat =
				tileBounds.north -
				((i + 0.5) * (tileBounds.north - tileBounds.south)) / res
			const lon =
				tileBounds.west +
				((j + 0.5) * (tileBounds.east - tileBounds.west)) / res
			const val = getPixelValue(lat, lon)
			ctx.fillStyle = getColor(val)
			ctx.fillRect(j * step, i * step, step, step)
		}
	}
}

function getTileLatLonBounds(x, y, z) {
	const n = Math.PI - (2 * Math.PI * y) / Math.pow(2, z)
	return {
		north: (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))),
		south:
			(180 / Math.PI) *
			Math.atan(
				0.5 *
					(Math.exp(n - (2 * Math.PI) / Math.pow(2, z)) -
						Math.exp(-(n - (2 * Math.PI) / Math.pow(2, z)))),
			),
		west: (x / Math.pow(2, z)) * 360 - 180,
		east: ((x + 1) / Math.pow(2, z)) * 360 - 180,
	}
}

onMounted(() => {
	nextTick(drawTile)
})
</script>

<template>
	<canvas
		:width="size"
		:height="size"
		ref="canvas"
		:style="{
			position: 'absolute',
			left: coords.x * size + 'px',
			top: coords.y * size + 'px',
		}"
	/>
</template>
