import { c3sblue, c3sred, c3steal } from '@/assets/styles/colors'

// Events are drawn with multiply compositing, so every one that covers a pixel
// darkens it again. A fixed opacity therefore only reads well at one event
// count: what shows structure for a few hundred goes to a solid block for
// several thousand, and what suits several thousand is barely visible for a
// few hundred. Scale it so that the ink laid down stays roughly constant.
//
// Each type gets its own figure. They are drawn in their own colours and there
// are far fewer wet events than hot or cold ones, so no single value suits
// both, least of all in the modes that show two types at once.
const ALPHA_REFERENCE = 250
const MIN_ALPHA = 0.02
const MAX_ALPHA = 0.35

export const heatmapAlpha = (count: number): number =>
	Math.min(
		MAX_ALPHA,
		Math.max(MIN_ALPHA, ALPHA_REFERENCE / Math.max(1, count)),
	)

export const heatmapAlphasByType = (
	events: { event_type: EventType }[],
): Record<EventType, number> => {
	const counts: Record<EventType, number> = { hot: 0, cold: 0, wet: 0 }
	for (const event of events) {
		if (event.event_type in counts) counts[event.event_type]++
	}
	return {
		hot: heatmapAlpha(counts.hot),
		cold: heatmapAlpha(counts.cold),
		wet: heatmapAlpha(counts.wet),
	}
}

// How many overlapping events it takes to get within a few percent of the
// darkest the stack will go, since (1 - alpha) raised to 3 / alpha is about
// e^-3. This is where the colour scale ends, so that it ends where the map
// stops changing rather than at an arbitrary number.
export const heatmapScaleMax = (alpha: number): number => Math.round(3 / alpha)

export const renderToContext = (
	ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
	events: {
		total_region: number[][]
		event_type: EventType
		id: string
	}[],
	mapState: { scale: number; transformation: any; pixelOrigin: any },
) => {
	ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)

	const alphas = heatmapAlphasByType(events)

	ctx.globalCompositeOperation = 'multiply'
	for (const event of events) {
		// ctx.globalCompositeOperation = event.event_type === 'hot' ? 'multiply' : 'lighten'
		ctx.beginPath()
		for (const ring of event.total_region || []) {
			// @ts-ignore
			ring.forEach(([lat, lng], i) => {
				// @ts-ignore
				const point = latLngToLayerPoint(lat, lng, mapState)
				if (i === 0) ctx.moveTo(point.x, point.y)
				else ctx.lineTo(point.x, point.y)
			})
			// @ts-ignore
			ring.forEach(([lat, lng], i) => {
				// @ts-ignore
				const point = latLngToLayerPoint(lat, lng - 360, mapState)
				if (i === 0) ctx.moveTo(point.x, point.y)
				else ctx.lineTo(point.x, point.y)
			})
			// @ts-ignore
			ring.forEach(([lat, lng], i) => {
				// @ts-ignore

				const point = latLngToLayerPoint(lat, lng + 360, mapState)
				if (i === 0) ctx.moveTo(point.x, point.y)
				else ctx.lineTo(point.x, point.y)
			})
		}
		ctx.closePath()
		const alpha = alphas[event.event_type]
		ctx.fillStyle = (
			event.event_type === 'hot'
				? c3sred
				: event.event_type === 'cold'
					? c3sblue
					: c3steal
		)
			.replace(')', `,${alpha})`)
			.replace('rgb', 'rgba')
		ctx.fill()
	}
}

let startI = 0
self.onmessage = async (
	e: MessageEvent<{
		canvas: OffscreenCanvas
		events: {
			total_region: number[][]
			event_type: EventType
			id: string
		}[]
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
