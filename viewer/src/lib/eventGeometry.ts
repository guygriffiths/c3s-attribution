/**
 * Packed event footprint geometry.
 *
 * Every event carries a polygon footprint for each day it ran, plus the union
 * of all of them. Across the catalogue that is around three million coordinate
 * pairs. As nested JavaScript arrays they cost hundreds of megabytes of heap,
 * and about a second of structured-clone time to get out of the fetch worker -
 * spent on the main thread, in unpredictable chunks, while the user is trying
 * to scrub the time reel.
 *
 * So the worker flattens them into typed arrays, which transfer for free, and
 * the main thread expands only the handful of rings it is about to draw.
 *
 * Coordinates are stored as integers on a 1/64 degree grid. The catalogue is
 * already quantised to 0.25 degrees bar a few thousand strays, so this is
 * exact for all but 0.16% of the values, and rounds those by at most 1/128 of
 * a degree - well under a kilometre, on footprints derived from cells 28km
 * across. Int16 then spans +-511.98 degrees, which leaves room for the wrapped
 * longitudes the dataset uses and a good deal more besides.
 */

export const GEOM_SCALE = 64

/**
 * One batch's worth of geometry, flattened.
 *
 * Rings are held in a single coordinate array, and everything else is a table
 * of offsets into it. The total footprints come first, then every timestep, so
 * that any run of rings is a pair of offsets rather than a search.
 */
export interface PackedGeometry {
	/** Interleaved lat, lng for every ring in the batch, scaled by GEOM_SCALE. */
	coords: Int16Array
	/** First coordinate pair of ring r. Length nRings + 1, so ring r ends at ringStart[r + 1]. */
	ringStart: Int32Array
	/** Total footprint of event i is rings [totalStart[i], totalStart[i + 1]). */
	totalStart: Int32Array
	/** Timesteps of event i are [eventStart[i], eventStart[i + 1]) in timeStart. */
	eventStart: Int32Array
	/** Timestep s is rings [timeStart[s], timeStart[s + 1]). */
	timeStart: Int32Array
}

/** Where an event's geometry lives: which batch, and which event within it. */
export interface GeomRef {
	g: PackedGeometry
	i: number
}

type Ring = [number, number][]

/**
 * Flatten a batch of freshly parsed events, and strip the geometry off them.
 *
 * Call this in the worker. The events are mutated: `regions`, `total_region`
 * and `pixel_set` are removed, since between them they are most of the weight
 * of a batch and nothing on the main thread reads them directly.
 */
export const packGeometry = (events: any[]): PackedGeometry => {
	// Measure first so the buffers can be allocated once.
	let nRings = 0
	let nPairs = 0
	let nSteps = 0
	for (const event of events) {
		for (const ring of event.total_region || []) {
			nRings++
			nPairs += ring.length
		}
		const regions = event.regions || []
		nSteps += event.times.length
		for (let t = 0; t < event.times.length; t++) {
			for (const ring of regions[t] || []) {
				nRings++
				nPairs += ring.length
			}
		}
	}

	const coords = new Int16Array(nPairs * 2)
	const ringStart = new Int32Array(nRings + 1)
	const totalStart = new Int32Array(events.length + 1)
	const eventStart = new Int32Array(events.length + 1)
	const timeStart = new Int32Array(nSteps + 1)

	let r = 0
	let p = 0
	let s = 0

	const writeRing = (ring: Ring) => {
		ringStart[r++] = p
		for (const [lat, lng] of ring) {
			coords[p * 2] = Math.round(lat * GEOM_SCALE)
			coords[p * 2 + 1] = Math.round(lng * GEOM_SCALE)
			p++
		}
	}

	for (let i = 0; i < events.length; i++) {
		totalStart[i] = r
		for (const ring of events[i].total_region || []) writeRing(ring)
	}
	totalStart[events.length] = r

	for (let i = 0; i < events.length; i++) {
		const event = events[i]
		eventStart[i] = s
		const regions = event.regions || []
		// Indexed by time rather than by what happens to be in `regions`, so that
		// a short or missing entry becomes an empty timestep instead of shifting
		// every following day onto the wrong footprint.
		for (let t = 0; t < event.times.length; t++) {
			timeStart[s++] = r
			for (const ring of regions[t] || []) writeRing(ring)
		}
	}
	eventStart[events.length] = s
	timeStart[nSteps] = r
	ringStart[nRings] = p

	for (const event of events) {
		delete event.regions
		delete event.total_region
		// Only ever read to build the pixel index, which the worker has just done.
		delete event.pixel_set
	}

	return { coords, ringStart, totalStart, eventStart, timeStart }
}

/** The buffers to hand to postMessage as transferables. */
export const geometryTransferables = (g: PackedGeometry): ArrayBuffer[] => [
	g.coords.buffer as ArrayBuffer,
	g.ringStart.buffer as ArrayBuffer,
	g.totalStart.buffer as ArrayBuffer,
	g.eventStart.buffer as ArrayBuffer,
	g.timeStart.buffer as ArrayBuffer,
]

const expand = (g: PackedGeometry, from: number, to: number): Ring[] => {
	const { coords, ringStart } = g
	const rings: Ring[] = []
	for (let r = from; r < to; r++) {
		const start = ringStart[r]
		const end = ringStart[r + 1]
		const ring: Ring = new Array(end - start)
		for (let p = start; p < end; p++) {
			ring[p - start] = [
				coords[p * 2] / GEOM_SCALE,
				coords[p * 2 + 1] / GEOM_SCALE,
			]
		}
		rings.push(ring)
	}
	return rings
}

/**
 * The union of everywhere an event reached, as rings of [lat, lng].
 *
 * Events fetched individually rather than from the catalogue carry their
 * geometry as plain arrays, so both shapes are accepted.
 */
export const totalRegionOf = (event: ExtremeEvent): Ring[] => {
	const ref = event.geom
	if (!ref) return event.total_region || []
	return expand(ref.g, ref.g.totalStart[ref.i], ref.g.totalStart[ref.i + 1])
}

/** Where an event reached on one of its days, as rings of [lat, lng]. */
export const regionAt = (event: ExtremeEvent, timeIdx: number): Ring[] => {
	const ref = event.geom
	if (!ref) return event.regions?.[timeIdx] || []
	const g = ref.g
	const s = g.eventStart[ref.i] + timeIdx
	if (timeIdx < 0 || s >= g.eventStart[ref.i + 1]) return []
	return expand(g, g.timeStart[s], g.timeStart[s + 1])
}

/**
 * Walk the vertices of an event's total footprint without building any arrays.
 *
 * `i` counts from zero within each ring, so a canvas path can move to the
 * first vertex of a ring and line to the rest, exactly as it would when
 * iterating the nested form.
 */
export const eachTotalRegionVertex = (
	event: ExtremeEvent,
	visit: (lat: number, lng: number, i: number) => void,
) => {
	const ref = event.geom
	if (!ref) {
		for (const ring of event.total_region || []) {
			for (let i = 0; i < ring.length; i++) visit(ring[i][0], ring[i][1], i)
		}
		return
	}
	const g = ref.g
	// Pulled out of the loop so the inner reads go straight to the buffers.
	const { coords, ringStart, totalStart } = g
	for (let r = totalStart[ref.i]; r < totalStart[ref.i + 1]; r++) {
		const start = ringStart[r]
		const end = ringStart[r + 1]
		for (let p = start; p < end; p++) {
			visit(
				coords[p * 2] / GEOM_SCALE,
				coords[p * 2 + 1] / GEOM_SCALE,
				p - start,
			)
		}
	}
}
