/// <reference lib="webworker" />
import { booleanContains, point, polygon } from '@turf/turf';
import Flatbush from 'flatbush';

// For ultra-fast bounding box search
let spatialIndex: Flatbush | null = null

// let eventPixelSets: Set<number>[] = []
let eventPolygons: { poly: ReturnType<typeof polygon>; idx: number }[] = []
let eventBboxes: [number, number, number, number][] = []

const packCoord = ([lat, lon]: [number, number]): number => {
	const latInt = Math.round((lat + 90) * 4)
	const lonInt = Math.round((lon + 180) * 4)
	return (latInt << 12) | lonInt // 12 bits for lon (0–1440), 20 bits for lat
}

self.onmessage = (e: MessageEvent) => {
	const { type, payload } = e.data

	if (type === 'init') {
		eventBboxes = payload.eventBboxes

		// const eventPixelArrays: [number, number][] = payload.eventPixelArrays
		const eventTotalRegions: [number, number][][] = payload.eventTotalRegions

		// Build spatial index for initial check
		spatialIndex = new Flatbush(eventBboxes.length, 2)
		eventBboxes.forEach((bbox, i) => {
			// Add the bounding box to the spatial index
			spatialIndex!.add(
				bbox[0], // minX
				bbox[1], // minY
				bbox[2], // maxX
				bbox[3], // maxY
			)
		})
		spatialIndex!.finish()

		// Create polygons for each event
		eventPolygons = eventTotalRegions.map((region, idx) => {
			// Create a polygon from the total region coordinates
			return {
				poly: polygon([region]),
				idx: idx,
			}	
		})

		// once we have pixel_sets for each event
		// for (const pixel of eventPixelArrays) {
		// 	// Add each pixel to the corresponding set
		// 	if (!eventPixelSets[i]) {
		// 		eventPixelSets[i] = new Set()
		// 	}
		// 	eventPixelSets[i].add(packCoord(pixel))
		// }
		self.postMessage({ type: 'ready' })
		console.log(
			'Event filter worker initialized with',
			eventBboxes.length,
			'events',
		)
	}

	if (type === 'filter') {
		if (!spatialIndex) {
			self.postMessage({ type: 'result', data: [] })
			return
		}
		// console.log('Filtering point', payload.point)
		
		const [lat, lon] = payload.point
		const p = point([lat, lon])
		
		const candidateIdxes = spatialIndex!.search(lat, lon, lat, lon)
		const candidateSet = new Set(candidateIdxes)
		// console.log('Filtering point', payload.point, 'got', candidateIdxes.length, 'candidates', candidateIdxes)

		const filtered = eventPolygons.filter((eventPolygon) => {
			if (!candidateSet.has(eventPolygon.idx)) return false
			// console.log('testing candidate event', idx, eventPolygon, 'for point', p)
			// TODO temporary - we want the below really
			if (booleanContains(eventPolygon.poly, p)) {
				// console.log('Point', payload.point, 'intersects event', idx)
				return true
			}
			return false
			// TODO - Once we have event pixels
			// return (
			// 	candidateSet.has(event.id) &&
			// 	eventPixelSets[event.id].has(packCoord([lat, lon]))
			// )
		}).map(ep => ep.idx)


		self.postMessage({ type: 'result', data: filtered })
	}
}
