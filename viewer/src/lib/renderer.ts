// lib/renderer.ts
import { differenceInDays } from 'date-fns'
import L from 'leaflet'
import { h } from 'vue'

export const TILE_SIZE = 256
export const LL_STEP = 0.25

const snap025 = (n: number) => Math.round(n * 4) / 4

type GeometryFunc = (
	lat: number,
	lon: number,
) => { x: number; y: number; w: number; h: number } | null

export const getTileGeometry = (
	coords: any,
	leafletObj: L.GridLayer,
): GeometryFunc => {
	// const key = `${z}-${x}-${y}`
	// if (tileGeometryCache.has(key)) return tileGeometryCache.get(key)

	// const bounds = leafletObj._tileCoordsToBounds(coords)
	// console.log('getTileGeometry', coords, leafletObj)
	// TODO Cache this? I think it's more-or-less different for each event/tile combo. Not actually, but practically.
	const nwPoint = L.point(coords.x * TILE_SIZE, coords.y * TILE_SIZE)
	const sePoint = L.point(
		(coords.x + 1) * TILE_SIZE,
		(coords.y + 1) * TILE_SIZE,
	)

	const map = (leafletObj as any)._map as L.Map
	const nw = map.unproject(nwPoint, coords.z)
	const se = map.unproject(sePoint, coords.z)

	const bounds = L.latLngBounds(nw, se)
	const originX = coords.x * TILE_SIZE
	const originY = coords.y * TILE_SIZE
	const step = LL_STEP

	const latValues = []
	for (
		let lat = bounds.getSouth() - step;
		lat <= bounds.getNorth() + step;
		lat += step
	) {
		latValues.push(snap025(lat))
	}
	const lonValues = []
	for (
		let lon = bounds.getWest() - step;
		lon <= bounds.getEast() + step;
		lon += step
	) {
		lonValues.push(snap025(lon))
	}

	// Calculate consistent width/height for tiles
	const w = Math.ceil(
		map.project(L.latLng(latValues[0], lonValues[1]), coords.z).x -
			map.project(L.latLng(latValues[0], lonValues[0]), coords.z).x,
	)
	const h = Math.ceil(
		map.project(L.latLng(latValues[0], lonValues[0]), coords.z).y -
			map.project(L.latLng(latValues[1], lonValues[0]), coords.z).y,
	)
	const wAdjusted = w + 1
	const hAdjusted = h + 1

	const geometry = new Array(latValues.length * lonValues.length)
	let index = 0

	for (const lat of latValues) {
		for (const lon of lonValues) {
			const point = map.project(L.latLng(lat, lon), coords.z)
			const x = Math.floor(point.x - originX)
			const y = Math.floor(point.y - originY)
			// if (x < 0 || x > TILE_SIZE - 1 || y < 0 || y > TILE_SIZE - 1) {
			// 	geometry[index++] = null
			// } else {
			geometry[index++] = {
				x: x - Math.floor(wAdjusted / 2),
				y: y - Math.floor(hAdjusted / 2),
				w: wAdjusted,
				h: hAdjusted,
			}
			// }
		}
	}
	const latMap = new Map(latValues.map((v, i) => [v.toFixed(3), i]))
	const lonMap = new Map(lonValues.map((v, i) => [v.toFixed(3), i]))

	const geomFunc = (lat: number, lon: number) => {
		const latIndex = latMap.get(snap025(lat).toFixed(3))
		const lonIndex = lonMap.get(snap025(lon).toFixed(3))
		if (latIndex == null || lonIndex == null) return null
		return geometry[latIndex * lonValues.length + lonIndex]
	}

	// tileGeometryCache.set(key, geomFunc)
	return geomFunc
}

interface EventTileKey {
	coords: { x: number; y: number; z: number }
	t: number
	id: string
	key: string
}

export const eventTileKey = (
	coords: { x: number; y: number; z: number },
	t: number,
	id: string,
): EventTileKey => ({
	coords,
	t,
	id,
	key: `${coords.x}-${coords.y}-${coords.z}-${t}-${id}`,
})

const tileImageCache = new Map<string, HTMLCanvasElement>()

export const getCanvasFromCache = (
	key: EventTileKey,
	selectedEvent: ExtremeEventFull | null,
	selectedTime: Date,
	viewMode: ViewMode,
	intensityRange: [number, number],
	eventHeatmapRef: any | null,
	colorForValue: (v: number) => string,
	intensityForValue: (v: number) => number,
) => {
	if (tileImageCache.has(key.key)) {
		// console.log('Cache hit for tile:', key.key)
		return tileImageCache.get(key.key)!
	}
	const canvas = document.createElement('canvas')
	canvas.width = TILE_SIZE
	canvas.height = TILE_SIZE
	const ctx = canvas.getContext('2d')
	if (!ctx) {
		console.error('Failed to get canvas context')
		return canvas
	}

	const layer = eventHeatmapRef
	if (layer?.leafletObject == undefined) {
		return canvas
	}

	let latLonValues: number[][] = []
	let dataValues: number[] = []
	if (viewMode === 'timemachine') {
		const selectedIndex =
			differenceInDays(selectedTime, selectedEvent?.times[0]!) || 0
		latLonValues = selectedEvent?.slices[selectedIndex] || []
		dataValues = selectedEvent?.values[selectedIndex].map(intensityForValue) || []
	} else {
		latLonValues = selectedEvent?.pixel_set || []
		dataValues = selectedEvent?.pixel_peak_values.map(intensityForValue) || []
	}

	const geometry = getTileGeometry(key.coords, layer.leafletObject)

	for (let i = 0; i < latLonValues.length; i++) {
		const latLon = latLonValues[i]
		const dataValue = dataValues[i]
		if (dataValue === undefined) continue

		const geom = geometry(latLon[0], latLon[1])
		if (!geom) continue

		ctx.fillStyle = colorForValue(dataValue)
		ctx.fillRect(geom.x, geom.y, geom.w, geom.h)
	}

	tileImageCache.set(key.key, canvas)

	return canvas
}

export const drawEventTile =
	(
		props: any,
		selectedEvent: ExtremeEventFull | null,
		selectedTime: Date,
		viewMode: ViewMode,
		intensityRange: [number, number],
		eventHeatmapRef: any | null,
		colorForValue: (v: number) => string,
		intensityForValue: (v: number) => number,
	) =>
	() => {
		const key = eventTileKey(
			props.coords,
			selectedEvent
				? differenceInDays(selectedTime, selectedEvent.times[0])
				: 0,
			selectedEvent?.id || '0',
		)

		console.log('Drawing event tile', intensityRange, intensityForValue, colorForValue)

		const canvas = document.createElement('canvas')
		canvas.width = TILE_SIZE
		canvas.height = TILE_SIZE
		const ctx = canvas.getContext('2d')

		const tileCanvas = getCanvasFromCache(
			key,
			selectedEvent,
			selectedTime,
			viewMode,
			intensityRange,
			eventHeatmapRef,
			colorForValue,
			intensityForValue,
		)

		if (ctx !== null) {
			ctx.drawImage(tileCanvas, 0, 0)
		} else {
			console.error('Failed to get canvas context for event tile')
		}

		return h('canvas', {
			width: TILE_SIZE,
			height: TILE_SIZE,
			ref: (el) => {
				if (el && el !== canvas) {
					// @ts-ignore
					el.replaceWith(canvas)
				}
			},
		})
	}
