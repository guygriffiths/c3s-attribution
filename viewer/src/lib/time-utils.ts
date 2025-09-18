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
		const color = alternateYears
			? year % 2 === 0
				? i % 2 === 0
					? 'rgba(0, 0, 0, 0.0)'
					: 'rgba(0, 0, 0, 0.05)'
				: i % 2 === 0
					? 'rgba(0, 0, 0, 0.05)'
					: 'rgba(0, 0, 0, 0.0)'
			: i % 2 === 0
				? 'rgba(0, 0, 0, 0.05)'
				: 'rgba(0, 0, 0, 0.0)'

		return {
			name: month.name,
			startX: monthStartX,
			length: month.length,
			color,
		}
	})
}

export const dayStr = (day: number, year: number) => {
	day = Math.max(1, Math.min(day, TOTAL_DAYS))
	const date = setDayOfYear(new Date(year, 0, 1), day)
	return format(date, 'do MMMM')
}

export function assignTimelinePositions(
	events: WeatherEvent[],
	targetYear: number,
) {
	const yearStart = new Date(targetYear, 0, 0).getTime()
	const yearEnd = new Date(targetYear + 1, 0, 0).getTime() - 1

	// Step 1: Filter and slice in one go, reuse timestamps to avoid creating Date objects
	const sliced: (WeatherEvent & { startX: number; endX: number })[] = []
	for (let i = 0; i < events.length; i++) {
		const e = events[i]
		const first = e.times[0]
		const last = e.times[e.times.length - 1]

		if (last.getTime() <= yearStart || first.getTime() > yearEnd) continue

		const startX = first.getTime() < yearStart ? 1 : getDayOfYear(first)
		const endX =
			last.getTime() > yearEnd
				? (yearEnd - yearStart) / 86400000
				: getDayOfYear(last)

		// if (e.id === '1997122808350229') {
		// 	console.log('Weird event running from:', first, 'to', last)
		// 	console.log('Event is part of year', targetYear)
		// 	console.log(last, 'is after or equal to', new Date(yearStart))
		// 	console.log('AND')
		// 	console.log(first, 'is before or equal to', new Date(yearEnd))
		// 	console.log()
		// }
		sliced.push({ ...e, startX, endX })
	}

	// Step 2: Assign y-positions using a greedy row-packing algorithm
	const rows: number[] = [] // row[y] = lastEndX
	const result = new Array(sliced.length)

	sliced.sort((a, b) => a.startX - b.startX)

	let maxY = 0
	for (let i = 0; i < sliced.length; i++) {
		const e = sliced[i]
		let y = 0
		for (; y < rows.length; y++) {
			if (rows[y] < e.startX) break
		}
		e.y = y
		rows[y] = e.endX
		if (y > maxY) maxY = y
		result[i] = e
	}

	return { events: result, maxEvents: maxY }
}
