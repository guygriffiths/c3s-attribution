import { useLabels } from '@/lib/labels'
import { format, setDayOfYear } from 'date-fns'

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
					? 'rgba(0, 0, 0, 0.1)'
					: 'rgba(0, 0, 0, 0.15)'
				: i % 2 === 0
					? 'rgba(0, 0, 0, 0.05)'
					: 'rgba(0, 0, 0, 0.1)'
			: i % 2 === 0
				? 'rgba(0, 0, 0, 0.1)'
				: 'rgba(0, 0, 0, 0.05)'
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
