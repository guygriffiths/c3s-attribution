import { c3sblue, c3sred } from '@/assets/styles/colors'
export { }

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
		const alpha = 0.1
		ctx.fillStyle = (event.event_type === 'hot' ? c3sred : c3sblue)
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
	if(!canvas) return

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
