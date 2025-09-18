import { packPixelToInt } from '../utils'
export { }


self.onmessage = (e: MessageEvent) => {
	const events = e.data as {
		pixel_set?: [number, number][]
	}[]

	const pixelIndex: Record<number, number[]> = {}

	for (let idx =0; idx < events.length; idx++) {
		const event = events[idx]
		if (!event.pixel_set) continue
		for (let [lat,lon] of event.pixel_set) {
			const pid = packPixelToInt(lat, lon)
			if (!pixelIndex[pid]) {
				pixelIndex[pid] = []
			}
			pixelIndex[pid].push(idx)
		}
	}

	self.postMessage(pixelIndex)
}
