import { c3sblue, c3sred, c3steal } from '@/assets/styles/colors'
import { eachTotalRegionVertex } from '@/lib/eventGeometry'

// Events are drawn with multiply compositing, so every one that covers a pixel
// darkens it again, and the opacity decides how many overlapping events it
// takes to reach full colour. It is deliberately fixed rather than taken from
// what is on screen: a shade has to mean the same number of events whatever
// the time window is set to, or the scale beside the map is only true for the
// instant it was drawn.
//
// Each type gets its own figure. They are drawn in their own colours and the
// dataset yields far fewer wet events than hot or cold ones, so no single
// value suits them all, least of all in the modes showing two types at once.
//
// Calibrated for the default ten year window, over which the dataset produces
// roughly 2000 hot, 1000 cold and 200 wet events, from 250 / count capped at
// 0.35. Tune them by eye if the balance looks wrong: nothing else needs to
// change, because the scale is built from the same numbers.
export const HEATMAP_ALPHAS: Record<EventType, number> = {
	hot: 0.12,
	cold: 0.12,
	wet: 0.3,
}

// How many overlapping events it takes to get within a few percent of the
// darkest the stack will go, since (1 - alpha) raised to 3 / alpha is about
// e^-3. This is where the colour scale ends, so that it ends where the map
// stops changing rather than at an arbitrary number.
export const heatmapScaleMax = (alpha: number): number => Math.round(3 / alpha)

const HEATMAP_COLORS: Record<EventType, string> = {
	hot: c3sred,
	cold: c3sblue,
	wet: c3steal,
}

// Both the worker and the region overlay in Map.vue fill from this, so an
// event is the same colour whichever of the two draws it.
export const heatmapFillStyle = (
	eventType: EventType,
	alpha: number,
): string =>
	(HEATMAP_COLORS[eventType] ?? c3steal)
		.replace(')', `,${alpha})`)
		.replace('rgb', 'rgba')

export const renderToContext = (
	ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
	events: ExtremeEvent[],
	mapState: { scale: number; transformation: any; pixelOrigin: any },
) => {
	ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)

	ctx.globalCompositeOperation = 'multiply'
	for (const event of events) {
		// ctx.globalCompositeOperation = event.event_type === 'hot' ? 'multiply' : 'lighten'
		ctx.beginPath()
		// Drawn three times over so that footprints crossing the antimeridian
		// appear on whichever copy of the world is on screen. Each pass is its own
		// set of subpaths, so it makes no difference to the fill that they are no
		// longer interleaved ring by ring.
		for (const wrap of [0, -360, 360]) {
			eachTotalRegionVertex(event, (lat, lng, i) => {
				const point = latLngToLayerPoint(lat, lng + wrap, mapState)
				if (i === 0) ctx.moveTo(point.x, point.y)
				else ctx.lineTo(point.x, point.y)
			})
		}
		ctx.closePath()
		ctx.fillStyle = heatmapFillStyle(
			event.event_type,
			HEATMAP_ALPHAS[event.event_type],
		)
		ctx.fill()
	}
}

let startI = 0
self.onmessage = async (
	e: MessageEvent<{
		canvas: OffscreenCanvas
		// Only ever sent empty, to prime the GPU cache. Real events are drawn on
		// the main thread, which already holds the packed geometry; posting them
		// here would clone a copy of the batch buffers for every event.
		events: ExtremeEvent[]
		mapState: { scale: number; transformation: any; pixelOrigin: any }
	}>,
) => {
	const { canvas, events, mapState } = e.data
	if (!canvas) return

	const ctx = canvas.getContext('2d') as
		| CanvasRenderingContext2D
		| OffscreenCanvasRenderingContext2D

	if (!ctx) return

	renderToContext(ctx, events, mapState)
	const bitmap = canvas.transferToImageBitmap()
	self.postMessage({
		bitmap: bitmap,
	})
}

export const latLngToLayerPoint = (
	lat: number,
	lng: number,
	mapState: {
		scale: number
		transformation: any
		pixelOrigin: any
	},
) => {
	const { scale, transformation, pixelOrigin } = mapState

	// Convert lat/lng to projected coordinates (Web Mercator)
	const R = 6378137 // Earth's radius in meters
	const MAX_LATITUDE = 85.0511287798

	const d = Math.PI / 180
	const max = MAX_LATITUDE
	const clampedLat = Math.max(Math.min(max, lat), -max)
	const sin = Math.sin(clampedLat * d)

	const projectedX = R * lng * d
	const projectedY = (R * Math.log((1 + sin) / (1 - sin))) / 2

	// Apply transformation
	const point = {
		x: scale * (transformation._a * projectedX + transformation._b),
		y: scale * (transformation._c * projectedY + transformation._d),
	}

	// Convert to layer point
	return {
		x: Math.round(point.x - pixelOrigin.x),
		y: Math.round(point.y - pixelOrigin.y),
	}
}
