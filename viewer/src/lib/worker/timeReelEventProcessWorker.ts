import * as d3 from 'd3'
import { getEventBoxes } from '../time-utils'

export { }

let startI = 0
self.onmessage = async (
	e: MessageEvent<{
		events: {
			times: number[]
			event_type: 'hot' | 'cold'
			id: string
			color: string
		}[]
		years: number[]
		mixedEvents: boolean
		start: number
		end: number
	}>,
) => {
	const { events, years, mixedEvents, start, end } = e.data
	// console.log('Time reel worker received message', years)

	const eventBoxesForYear: Record<number, any[]> = {}

	let maxSimultaneousEvents = 0
	for (let year of years) {
		const res = getEventBoxes(events, year, mixedEvents)
		eventBoxesForYear[year] = res.events
		maxSimultaneousEvents = Math.max(maxSimultaneousEvents, res.maxEvents)
	}

	const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24))
	const cwCounts = new Array(totalDays).fill(0)
	const hwCounts = new Array(totalDays).fill(0)
	let hotEventsActive = false
	let coldEventsActive = false
	events.forEach((event) => {
		event?.times.forEach((time: number) => {
			const daysFromStart = Math.floor((time - start) / (1000 * 60 * 60 * 24))

			if (event.event_type === 'cold') {
				cwCounts[daysFromStart] += 1
				coldEventsActive = true
			} else if (event.event_type === 'hot') {
				hwCounts[daysFromStart] += 1
				hotEventsActive = true
			}
		})
	})

	const newDs = getAreaString(
		hwCounts,
		hotEventsActive,
		cwCounts,
		coldEventsActive,
		years,
		start,
	)

	self.postMessage({
		newDs,
		eventBoxesForYear,
		maxSimultaneousEvents: maxSimultaneousEvents + 1,
	})
}

const getAreaString = (
	hotCounts: number[],
	hotActive: boolean,
	coldCounts: number[],
	coldActive: boolean,
	years: number[],
	startTime: number,
) => {
	// console.time('getAreaString')
	const data: Array<{ x: number; y0: number; y1: number }> =
		hotActive && coldActive
			? // Hot and cold events
				hotCounts.map((d, i) => ({
					x: i,
					y0: coldCounts[i],
					y1: d,
				}))
			: hotActive
				? // Hot events only
					hotCounts.map((d, i) => ({
						x: i,
						y0: d,
						y1: d,
					}))
				: // Cold events only
					coldCounts.map((d, i) => ({
						x: i,
						y0: d,
						y1: d,
					}))

	const yScale = d3
		.scaleLinear()
		.domain([
			0,
			Math.max(...data.map((d) => d.y0).concat(data.map((d) => d.y1)), 5),
		])
		.range([0, 0.5])

	const areaStr = d3
		.area<{ x: number; y0: number; y1: number }>()
		.x((d) => d.x)
		.y0((d) => yScale(d.y0))
		.y1((d) => -yScale(d.y1))
		.defined((d) => d.x >= 0 && d.x < hotCounts.length)
		.curve(d3.curveMonotoneX)

	const ret: Record<number, string> = {}
	for (let year of years) {
		const startOfYear = Date.UTC(year, 0, 1) // Jan 1 UTC
		const endOfYear = Date.UTC(year + 1, 0, 1) // Jan 1 next year UTC

		const startIdx = Math.max(
			0,
			Math.floor((startOfYear - startTime) / (1000 * 60 * 60 * 24)) - 1,
		)
		const endIdx = Math.min(
			data.length,
			Math.floor((endOfYear - startTime) / (1000 * 60 * 60 * 24)) + 1,
		)

		// We add 2 invisible moves to ensure that the centre of the object's bounding box is always at y=0
		// That way when we apply a vertical gradient, it is always centered
		ret[year] =
			areaStr(data.slice(startIdx, endIdx)) + ` M0,${-2} l0,0 M0,${2} l0,0` ||
			''
	}
	// console.timeEnd('getAreaString')
	return ret
}
