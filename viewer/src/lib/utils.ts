import { ExtremeEvent, MainStore } from "@/store/store"
import { bbox, booleanIntersects, multiPolygon, polygon, simplify } from "@turf/turf"
import { differenceInDays } from "date-fns"
import Flatbush from "flatbush"
import { Position } from "geojson"

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
  eventIndex: Flatbush | undefined,
  full: boolean = false,
  prefilteredCandidates?: number[], // new param for full
): ExtremeEvent[] => {
  let spatialCandidates: Set<number> | null = null

  console.log('Filtering events, full:', full, filters.wrafRegion)

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
          event.total_region.map((c) => [c[1], c[0]]),
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
  }

  const fe = events.filter((event: ExtremeEvent, i) => {
    if (spatialCandidates && !spatialCandidates.has(i)) return false

    if (!filters.includeOceanEvents && event.ocean_only) return false

    const duration =
      1 + differenceInDays(event.times[event.times.length - 1], event.times[0])
    if (duration < filters.duration) return false

    const intensity = event.intensity || 0
    if (intensity < filters.intensity) return false

    const sizePercentile = event.size || 0
    if (sizePercentile < filters.size) return false

    return true
  })

  console.log(
    `Filtered ${events.length} events to ${fe.length} based on full: ${full}, filters:`,
    filters,
  )

  return fe
}
