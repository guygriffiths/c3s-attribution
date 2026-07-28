import { useLabels } from '@/lib/labels'
import { format, getDayOfYear, setDayOfYear } from 'date-fns'

export const TOTAL_DAYS = 366

export const monthsForYear = (
	year: number,
	alternateYears: boolean = false,
	$l: ReturnType<typeof useLabels>['value'],
) => {
	const months = [
		{ name: $l.months.jan, length: 31 },
		{ name: $l.months.feb, length: year % 4 === 0 ? 29 : 28 },
		{ name: $l.months.mar, length: 31 },
		{ name: $l.months.apr, length: 30 },
		{ name: $l.months.may, length: 31 },
		{ name: $l.months.jun, length: 30 },
		{ name: $l.months.jul, length: 31 },
		{ name: $l.months.aug, length: 31 },
		{ name: $l.months.sep, length: 30 },
		{ name: $l.months.oct, length: 31 },
		{ name: $l.months.nov, length: 30 },
		{ name: $l.months.dec, length: 31 },
	]

	let startX = 0
	return months.map((month, i) => {
		const monthStartX = startX
		startX += month.length

		return {
			name: month.name,
			startX: monthStartX,
			length: month.length,
		}
	})
}

export const dayStr = (day: number, year: number, showYear: boolean) => {
	day = Math.max(1, Math.min(day, TOTAL_DAYS))
	const date = setDayOfYear(new Date(year, 0, 1), day)
	return format(date, 'dd MMM') + (showYear ? ` ${year}` : '')
}

export const dateStr = (date: Date) => {
	return dayStr(getDayOfYear(date), date.getUTCFullYear(), true)
}

export function getEventBoxes(
	events: {
		times: number[]
		id: string
		event_type: EventType
		color: string
	}[],
	year: number,
	eventMode: SelectedEventType,
): { events: EventBox[]; maxEvents: number } {
	// console.log('getEventBoxes', events, year, splitByEventType)
	// Step 1: Filter and slice in one go, reuse timestamps to avoid creating Date objects

	const yearStart = Date.UTC(year, 0, 1)
	const yearEnd = Date.UTC(year + 1, 0, 1) - 1

	const eventBars: EventBox[] = []
	for (let e of events.filter((e) => {
		const first = e.times[0]
		const last = e.times[e.times.length - 1]
		return first <= yearEnd && last >= yearStart
	})) {
		// Get startX and endX for this year
		const first = new Date(e.times[0])	
		const last = new Date(e.times[e.times.length - 1])

		let startX = getDayOfYear(first) + first.getUTCFullYear() * TOTAL_DAYS
		let endX = getDayOfYear(last) + last.getUTCFullYear() * TOTAL_DAYS

		eventBars.push({ eventId: e.id, startX: startX, endX: endX, y: 0, type: e.event_type, color: e.color })
	}

	// Step 2: Assign y-positions using a greedy row-packing algorithm

	let maxY = 0
	if (eventMode == 'hot' || eventMode == 'cold' || eventMode == 'wet') {
		const rows: number[] = [] // row[y] = lastEndX
		eventBars.sort((a, b) => a.startX - b.startX)

		for (let e of eventBars) {
			let y = 0
			for (; y < rows.length; y++) {
				if (rows[y] < e.startX) break
			}
			e.y = y
			rows[y] = e.endX
			if (y > maxY) maxY = y
		}
	} else {
		const topRows: number[] = [] // row[y] = lastEndX
		const btmRows: number[] = [] // row[y] = lastEndX
		let topVar
		let btmVar
		if (eventMode === 'hotwet') {
			topVar = 'hot'
			btmVar = 'wet'
		} else if (eventMode === 'coldwet') {
			topVar = 'cold'
			btmVar = 'wet'
		} else {
			topVar = 'hot'
			btmVar = 'cold'
		}

		for (let e of eventBars
			.filter((ev) => ev.type === topVar)
			.sort((a, b) => a.startX - b.startX)) {
			let y = 0
			for (; y < topRows.length; y++) {
				if (topRows[y] < e.startX) break
			}
			e.y = y
			topRows[y] = e.endX
			if (y > maxY) maxY = y
		}
		for (let e of eventBars
			.filter((ev) => ev.type === btmVar)
			.sort((a, b) => a.startX - b.startX)) {
			let y = 0
			for (; y < btmRows.length; y++) {
				if (btmRows[y] < e.startX) break
			}
			e.y = y
			btmRows[y] = e.endX
			if (y > maxY) maxY = y
		}
		maxY *= 2
	}

	return { events: eventBars, maxEvents: maxY }
}

export const intervalToMs = (interval: string): number => {
	const match = interval.match(/^(\d+(?:\.\d+)?)(ms|s|m|h|d)$/)
	if (!match) throw new Error(`Invalid interval: ${interval}`)
	const [, valueStr, unit] = match
	const value = parseFloat(valueStr)
	const multipliers: Record<string, number> = {
		ms: 1,
		s: 1000,
		m: 60_000,
		h: 3_600_000,
		d: 86_400_000,
	}
	return value * multipliers[unit]
}
