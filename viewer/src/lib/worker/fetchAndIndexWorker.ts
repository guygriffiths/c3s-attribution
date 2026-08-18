import { DATA_ROOT } from '@/lib/utils'

export { }

let startI = 0
self.onmessage = async (e: MessageEvent) => {
	// `active` requests the events still in progress rather than a finished year.
	// These are republished by the processing side every time step, so they have
	// no year of their own and are only ever loaded once, at startup.
	const { year, eventType, active } = e.data

	const url = active
		? `${DATA_ROOT}events-${eventType}-active.jsonl`
		: `${DATA_ROOT}events-${eventType}-${year}.jsonl`

	const events = await fetch(url)
		.then((r) => r.text())
		.then((t) => {
			const body = t.trim()
			// The active file is legitimately empty when nothing is in progress
			if (!body) return []
			return body.split('\n').map((line) => {
				const event = JSON.parse(line)
				// Convert to timestamps (numbers) instead of Date objects
				event.times = event.times.map((t: string) => new Date(t).getTime())
				return event
			})
		})
		.catch(() => [])

	// Build pixel index right here
	const pixelIndex: Record<number, number[]> = {}
	for (let idx = 0; idx < events.length; idx++) {
		const event = events[idx]
		if (!event.pixel_set) continue
		for (let pid of event.pixel_set) {
			if (!pixelIndex[pid]) {
				pixelIndex[pid] = []
			}
			pixelIndex[pid].push(idx + startI)
		}
	}
	// console.log(`Worker built pixel index for ${eventType} ${year}`)
	
	const dateIndex: Record<number, number[]> = {}
	const monthIndex: Record<string, number[]> = {}
	
	for (let idx = 0; idx < events.length; idx++) {
		const event = events[idx]
		for (let time of event.times) {
			if (!dateIndex[time]) {
				dateIndex[time] = []
			}
			dateIndex[time].push(idx + startI)

			const date = new Date(time)
			const monthKey = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
			if (!monthIndex[monthKey]) {
				monthIndex[monthKey] = []
			}
			monthIndex[monthKey].push(idx + startI)
		}
	}

	// console.log(`Worker built date index for ${eventType} ${year}`)
	startI += events.length

	self.postMessage({
		year,
		events,
		pixelIndex,
		dateIndex,
		monthIndex,
		eventType,
		active: !!active,
	})
}
