import { DATA_ROOT } from '@/lib/utils'

export { }

let startI = 0
self.onmessage = async (e: MessageEvent) => {
	const { year, prefix } = e.data

	const events = await fetch(`${DATA_ROOT}events-${prefix}-${year}.jsonl`)
		.then((r) => r.text())
		.then((t) =>
			t
				.trim()
				.split('\n')
				.map((line) => {
					const event = JSON.parse(line)
					// Convert to timestamps (numbers) instead of Date objects
					event.times = event.times.map((t: string) => new Date(t).getTime())
					return event
				}),
		)
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
	// console.log(`Worker built pixel index for ${prefix} ${year}`)
	
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

	// console.log(`Worker built date index for ${prefix} ${year}`)
	startI += events.length

	self.postMessage({ year, events, pixelIndex, dateIndex, monthIndex })
}
