export { }

self.onmessage = (e: MessageEvent) => {
	const { events, startI } = e.data as {
		events: {
			pixel_set?: number[]
		}[]
		startI: number
	}

	const pixelIndex: Record<number, number[]> = {}

	for (let idx = 0; idx < events.length; idx++) {
		const event = events[idx]
		if (!event.pixel_set) continue
		for (let pid of event.pixel_set) {
			// const pid = packPixelToInt(lat, lon)
			if (!pixelIndex[pid]) {
				pixelIndex[pid] = []
			}
			pixelIndex[pid].push(idx + startI)
		}
	}

	self.postMessage(pixelIndex)
}
