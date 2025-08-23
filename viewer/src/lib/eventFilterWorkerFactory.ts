export function createEventFilterWorker() {
	const worker = new Worker(
		new URL('./eventFilterWorker.ts', import.meta.url),
		{
			type: 'module',
		},
	)

	return {
		init(events: ExtremeEvent[]) {
			const eventBboxes = events.map((event) => event.bbox)
			const eventTotalRegions = events.map((event) => event.total_region)
			//   const eventPixelSets = events.map(event => event.pixel_set);
			worker.postMessage({
				type: 'init',
				payload: {
					eventBboxes: JSON.parse(JSON.stringify(eventBboxes)),
					eventTotalRegions: JSON.parse(JSON.stringify(eventTotalRegions)),
				},
			})
		},
		filter(point: [number, number]) {
			return new Promise((resolve) => {
				const handleMessage = (e: MessageEvent) => {
					if (e.data.type === 'result') {
						worker.removeEventListener('message', handleMessage)
						resolve(e.data.data)
					}
				}
				worker.addEventListener('message', handleMessage)
				worker.postMessage({
					type: 'filter',
					payload: { point: [point[0], point[1]]},
				})
			})
		},
		terminate() {
			worker.terminate()
		},
	}
}
