import { MainStore } from '@/store/store'
import {
	bbox,
	booleanIntersects,
	multiPolygon,
	polygon,
	simplify
} from '@turf/turf'
import Flatbush from 'flatbush'
import { Position } from 'geojson'

export const debounce = (func: (...args: any[]) => void, delay: number) => {
	let timeout: ReturnType<typeof setTimeout> | null = null
	return (...args: any[]) => {
		if (timeout) clearTimeout(timeout)
		timeout = setTimeout(() => {
			func(...args)
		}, delay)
	}
}

export const filterEvents = (
	events: ExtremeEvent[],
	filters: MainStore['filters'],
	eventIndex: Flatbush | null,
	full: boolean = false,
	prefilteredCandidates?: number[], // new param for full
): ExtremeEvent[] => {
	let spatialCandidates: Set<number> | null = null

	if (filters.wrafRegion && eventIndex) {
		const geom = filters.wrafRegion.geometry
		const turfRegion =
			geom.type === 'Polygon'
				? polygon(geom.coordinates)
				: multiPolygon(geom.coordinates)

		// Simplify once up front for speed
		const simplifiedRegion = simplify(turfRegion, {
			tolerance: 0.1,
			highQuality: false,
		})

		if (full) {
			// Only run the heavy region checks on the prefiltered candidates
			spatialCandidates = new Set()
			events.forEach((event, idx) => {
				const totalPoly = polygon([
					event.total_region.map((c: [number, number]) => [c[1], c[0]]),
				])
				if (booleanIntersects(simplifiedRegion, totalPoly)) {
					for (let region of event.regions) {
						const coords = region.map((c: [number, number]) => [c[1], c[0]])
						const eventPoly = polygon([coords])
						if (booleanIntersects(simplifiedRegion, eventPoly)) {
							spatialCandidates!.add(idx)
							break
						}
					}
				}
			})
		} else {
			// Non-full or no prefiltered candidates: run bbox-based prefilter
			const regionBboxes =
				geom.type === 'Polygon'
					? [bbox(turfRegion)]
					: turfRegion.geometry.coordinates.map((coords) =>
							bbox(polygon(coords as Position[][])),
						)

			spatialCandidates = new Set()
			regionBboxes.forEach((b) => {
				const candidates = eventIndex!.search(
					b[1], // minY
					b[0], // minX
					b[3], // maxY
					b[2], // maxX
				)
				candidates.forEach((candidate) => spatialCandidates!.add(candidate))
			})
		}
	} else if (false){//filters.selectedPoint) {
		// const p = point([filters.selectedPoint[1], filters.selectedPoint[0]]) // lon, lat
		// spatialCandidates = new Set()
		// events.forEach((event, idx) => {
		// 	const totalPoly = polygon([
		// 		event.total_region.map(([lat, lon]) => [lon, lat]),
		// 	])
		// 	if (booleanContains(totalPoly, p)) {
		// 		spatialCandidates!.add(idx)
		// 	}
		// })
		console.warn('Not filtering in main filter - we want to separate this logic')
		console.warn('You are going to just trigger the mini filter and turn down the opacity on the main heatmap. But the full filter will still run, so you will need to sort that out. It will just churn CPU otherwise')

	}

	const fe = events.filter((event: ExtremeEvent, i) => {
		if (spatialCandidates && !spatialCandidates.has(i)) return false

		if (!filters.includeOceanEvents && event.ocean_only) return false

		if (event.duration < filters.duration) return false

		const intensity = event.peak_value || 0
		if (intensity < filters.intensity) return false

		const pixelCount = event.pixel_count || 0
		if (pixelCount < filters.size) return false

		return true
	})

	// console.log(
	// 	`Filtered ${events.length} events to ${fe.length} based on full: ${full}, filters:`,
	// 	filters,
	// )

	return fe
}
