export { }

self.onmessage = (e: MessageEvent) => {
	const { events, startI } = e.data as {
		events: {
			times: Date[]
		}[]
		startI: number
	}

	const dateIndex: Record<string, number[]> = {}

	for (let idx = 0; idx < events.length; idx++) {
		const event = events[idx]
		for (let time of event.times) {
			const dateStr = time.toISOString().split('T')[0]
			if (!dateIndex[dateStr]) {
				dateIndex[dateStr] = []
			}
			dateIndex[dateStr].push(idx + startI)
		}
	}
	self.postMessage(dateIndex)
}
