/*
  chart-export.ts
  A small canvas toolkit for exporting freshly-rendered charts to PNG.
  Each chart component redraws its own data via these helpers rather than
  screenshotting the DOM, so exports are clean (no tooltips/buttons), on a
  white background, at a fixed, print-friendly size.
*/

export const EXPORT_WIDTH = 1024
export const EXPORT_HEIGHT = 768
const EXPORT_SCALE = 2

export const EXPORT_BG = '#ffffff'
export const AXIS_COLOR = '#444444'
export const TICK_COLOR = '#666666'
export const GRID_COLOR = '#e2e2e2'
export const TEXT_COLOR = '#1b1b1f'

export type Rect = { x: number; y: number; w: number; h: number }

export const DEFAULT_MARGIN = { top: 52, right: 24, bottom: 56, left: 74 }

export type ScaleFn = (v: number) => number

export type ExportContext = {
	canvas: HTMLCanvasElement
	ctx: CanvasRenderingContext2D
	width: number
	height: number
}

/** Create an offscreen canvas at the given CSS size, rendered at 2x for crispness. */
export function createExportCanvas(
	width = EXPORT_WIDTH,
	height = EXPORT_HEIGHT,
	background = EXPORT_BG,
): ExportContext {
	const canvas = document.createElement('canvas')
	canvas.width = width * EXPORT_SCALE
	canvas.height = height * EXPORT_SCALE
	const ctx = canvas.getContext('2d')!
	ctx.scale(EXPORT_SCALE, EXPORT_SCALE)
	ctx.fillStyle = background
	ctx.fillRect(0, 0, width, height)
	return { canvas, ctx, width, height }
}

/** Compute the inner plot rectangle for a canvas given margins. */
export function plotRect(
	width: number,
	height: number,
	margin = DEFAULT_MARGIN,
): Rect {
	return {
		x: margin.left,
		y: margin.top,
		w: Math.max(1, width - margin.left - margin.right),
		h: Math.max(1, height - margin.top - margin.bottom),
	}
}

/**
 * Resolve a CSS colour expression to a concrete colour usable on a canvas.
 * Handles `var(--x)` (optionally with a fallback) by reading the computed value
 * from the document root; passes through plain colours unchanged.
 */
export function resolveColor(expr: string | null | undefined): string {
	if (!expr) return TEXT_COLOR
	const trimmed = expr.trim()
	const varMatch = trimmed.match(/^var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$/)
	if (!varMatch) return trimmed
	const [, name, fallback] = varMatch
	const value = getComputedStyle(document.documentElement)
		.getPropertyValue(name)
		.trim()
	if (value) return resolveColor(value)
	if (fallback) return resolveColor(fallback)
	return TEXT_COLOR
}

/** Draw a centred chart title near the top of the canvas. */
export function drawTitle(
	ctx: CanvasRenderingContext2D,
	title: string,
	width: number,
	y = 30,
): void {
	if (!title) return
	ctx.save()
	ctx.fillStyle = TEXT_COLOR
	ctx.font =
		'600 20px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
	ctx.textAlign = 'center'
	ctx.textBaseline = 'middle'
	ctx.fillText(title, width / 2, y)
	ctx.restore()
}

function niceTicks(min: number, max: number, count = 5): number[] {
	if (!isFinite(min) || !isFinite(max) || min === max) return [min]
	const span = max - min
	const step0 = span / count
	const mag = Math.pow(10, Math.floor(Math.log10(step0)))
	const norm = step0 / mag
	const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : norm >= 1 ? 1 : 0.5) * mag
	const ticks: number[] = []
	const start = Math.ceil(min / step) * step
	for (let v = start; v <= max + step * 0.5; v += step) {
		ticks.push(Math.abs(v) < step * 1e-6 ? 0 : v)
	}
	return ticks
}

export type LinearAxesOpts = {
	plot: Rect
	xDomain: [number, number]
	yDomain: [number, number]
	xScale: ScaleFn
	yScale: ScaleFn
	xLabel?: string
	yLabel?: string
	xFormat?: (v: number) => string
	yFormat?: (v: number) => string
	grid?: boolean
}

const defaultFormat = (v: number): string => {
	if (v === 0) return '0'
	const a = Math.abs(v)
	if (a >= 1000 || a < 0.01) return v.toPrecision(3)
	return String(Math.round(v * 1000) / 1000)
}

/** Draw x/y axis lines, ticks, tick labels and axis titles for a linear plot. */
export function drawLinearAxes(
	ctx: CanvasRenderingContext2D,
	opts: LinearAxesOpts,
): void {
	const { plot, xDomain, yDomain, xScale, yScale } = opts
	const xFmt = opts.xFormat ?? defaultFormat
	const yFmt = opts.yFormat ?? defaultFormat
	ctx.save()
	ctx.font =
		'12px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

	const xTicks = niceTicks(xDomain[0], xDomain[1]).filter(
		(t) =>
			t >= Math.min(...xDomain) - 1e-9 && t <= Math.max(...xDomain) + 1e-9,
	)
	const yTicks = niceTicks(yDomain[0], yDomain[1]).filter(
		(t) =>
			t >= Math.min(...yDomain) - 1e-9 && t <= Math.max(...yDomain) + 1e-9,
	)

	// gridlines
	if (opts.grid !== false) {
		ctx.strokeStyle = GRID_COLOR
		ctx.lineWidth = 1
		for (const t of xTicks) {
			const px = xScale(t)
			ctx.beginPath()
			ctx.moveTo(px, plot.y)
			ctx.lineTo(px, plot.y + plot.h)
			ctx.stroke()
		}
		for (const t of yTicks) {
			const py = yScale(t)
			ctx.beginPath()
			ctx.moveTo(plot.x, py)
			ctx.lineTo(plot.x + plot.w, py)
			ctx.stroke()
		}
	}

	// axis lines
	ctx.strokeStyle = AXIS_COLOR
	ctx.lineWidth = 1.5
	ctx.beginPath()
	ctx.moveTo(plot.x, plot.y)
	ctx.lineTo(plot.x, plot.y + plot.h)
	ctx.lineTo(plot.x + plot.w, plot.y + plot.h)
	ctx.stroke()

	// x tick labels
	ctx.fillStyle = TICK_COLOR
	ctx.textAlign = 'center'
	ctx.textBaseline = 'top'
	for (const t of xTicks) {
		const px = xScale(t)
		ctx.strokeStyle = AXIS_COLOR
		ctx.beginPath()
		ctx.moveTo(px, plot.y + plot.h)
		ctx.lineTo(px, plot.y + plot.h + 4)
		ctx.stroke()
		ctx.fillText(xFmt(t), px, plot.y + plot.h + 7)
	}

	// y tick labels
	ctx.textAlign = 'right'
	ctx.textBaseline = 'middle'
	for (const t of yTicks) {
		const py = yScale(t)
		ctx.strokeStyle = AXIS_COLOR
		ctx.beginPath()
		ctx.moveTo(plot.x - 4, py)
		ctx.lineTo(plot.x, py)
		ctx.stroke()
		ctx.fillText(yFmt(t), plot.x - 7, py)
	}

	// axis titles
	ctx.fillStyle = TEXT_COLOR
	ctx.font =
		'600 13px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
	if (opts.xLabel) {
		ctx.textAlign = 'center'
		ctx.textBaseline = 'bottom'
		ctx.fillText(opts.xLabel, plot.x + plot.w / 2, plot.y + plot.h + 50)
	}
	if (opts.yLabel) {
		ctx.save()
		ctx.translate(18, plot.y + plot.h / 2)
		ctx.rotate(-Math.PI / 2)
		ctx.textAlign = 'center'
		ctx.textBaseline = 'top'
		ctx.fillText(opts.yLabel, 0, 0)
		ctx.restore()
	}
	ctx.restore()
}

/** Draw a date x-axis (~count evenly spaced ticks) at the bottom of a plot. */
export function drawDateAxis(
	ctx: CanvasRenderingContext2D,
	plot: Rect,
	dates: number[],
	bandCenter: (i: number) => number,
	count = 6,
): void {
	if (!dates.length) return
	ctx.save()
	ctx.font =
		'12px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
	ctx.fillStyle = TICK_COLOR
	ctx.textAlign = 'center'
	ctx.textBaseline = 'top'
	const n = dates.length
	const step = Math.max(1, Math.round(n / count))
	for (let i = 0; i < n; i += step) {
		const px = bandCenter(i)
		ctx.strokeStyle = AXIS_COLOR
		ctx.beginPath()
		ctx.moveTo(px, plot.y + plot.h)
		ctx.lineTo(px, plot.y + plot.h + 4)
		ctx.stroke()
		const label = new Date(dates[i]).toISOString().slice(0, 10)
		ctx.fillText(label, px, plot.y + plot.h + 7)
	}
	ctx.restore()
}

/** Trigger a PNG download of a rendered canvas. */
export function downloadCanvas(
	canvas: HTMLCanvasElement,
	filename: string,
): void {
	const url = canvas.toDataURL('image/png')
	const a = document.createElement('a')
	a.href = url
	a.download = filename.endsWith('.png') ? filename : `${filename}.png`
	a.click()
}
