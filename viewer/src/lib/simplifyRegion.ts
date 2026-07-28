import { simplify, truncate } from '@turf/turf'
import type {
    Feature,
    FeatureCollection,
    MultiPolygon,
    Polygon,
    Position,
} from 'geojson'

type RegionGeoJson =
	| Feature<Polygon | MultiPolygon>
	| FeatureCollection<Polygon | MultiPolygon>

// Conservative per-region budget, in characters of serialized JSON.
// localStorage is ~5MB total; with up to MAX_USER_REGIONS regions we keep each
// well under that so several can coexist with room to spare.
const TARGET_CHARS = 800_000

// Coordinate precision: the app filters events on a 0.25° (~28km) grid, so
// 4 decimal places (~11m) is far finer than needed and already trims most of
// the bloat from high-precision boundary exports.
const COORD_PRECISION = 4

// Douglas–Peucker tolerances (in degrees) tried in ascending order until the
// serialized region fits the budget.
const TOLERANCES = [0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]

const serializedSize = (g: unknown) => JSON.stringify(g).length

// A LinearRing must have at least 4 positions (and be closed). Simplification
// at high tolerance — or a malformed source file — can collapse a ring below
// that, which makes turf throw when the region is later used as a filter.
const ringIsValid = (ring: Position[]): boolean =>
	Array.isArray(ring) && ring.length >= 4

const sanitizePolygon = (rings: Position[][]): Position[][] | null => {
	if (!Array.isArray(rings) || rings.length === 0) return null
	const outer = rings[0]
	if (!ringIsValid(outer)) return null
	// Keep the outer ring plus any holes that are still valid; drop collapsed holes.
	const holes = rings.slice(1).filter(ringIsValid)
	return [outer, ...holes]
}

/**
 * Drop any ring/polygon/feature that has been reduced below the GeoJSON minimum
 * (4 positions per ring). Returns null if nothing valid remains.
 */
function sanitizeGeometry(geojson: RegionGeoJson): RegionGeoJson | null {
	const cleanFeature = (
		feature: Feature<Polygon | MultiPolygon>,
	): Feature<Polygon | MultiPolygon> | null => {
		const geom = feature.geometry
		if (geom.type === 'Polygon') {
			const coords = sanitizePolygon(geom.coordinates)
			if (!coords) return null
			return { ...feature, geometry: { type: 'Polygon', coordinates: coords } }
		}
		// MultiPolygon
		const polys = geom.coordinates
			.map(sanitizePolygon)
			.filter((p): p is Position[][] => p !== null)
		if (polys.length === 0) return null
		return { ...feature, geometry: { type: 'MultiPolygon', coordinates: polys } }
	}

	if (geojson.type === 'Feature') {
		return cleanFeature(geojson)
	}
	const features = geojson.features
		.map(cleanFeature)
		.filter((f): f is Feature<Polygon | MultiPolygon> => f !== null)
	if (features.length === 0) return null
	return { type: 'FeatureCollection', features }
}

export interface SimplifyResult {
	geojson: RegionGeoJson | null // null if nothing valid remained after sanitising
	simplified: boolean // true if Douglas–Peucker simplification was applied
	tooLarge: boolean // true if still over budget after the coarsest simplification
}

/**
 * Reduce a region's coordinate precision and, if still too large, progressively
 * simplify its geometry so it fits within the localStorage budget and renders
 * smoothly as a Leaflet vector overlay. Degenerate rings produced along the way
 * (or already present in the source) are stripped out.
 */
export function simplifyForStorage(input: RegionGeoJson): SimplifyResult {
	// 1. Always truncate coordinate precision — cheap and lossless for this app.
	let working: RegionGeoJson
	try {
		working = truncate(input as never, {
			precision: COORD_PRECISION,
			coordinates: 2,
			mutate: false,
		}) as RegionGeoJson
	} catch {
		working = input
	}

	if (serializedSize(working) <= TARGET_CHARS) {
		return {
			geojson: sanitizeGeometry(working),
			simplified: false,
			tooLarge: false,
		}
	}

	// 2. Escalate the simplification tolerance until it fits.
	let best = working
	for (const tolerance of TOLERANCES) {
		let candidate: RegionGeoJson
		try {
			candidate = simplify(working as never, {
				tolerance,
				highQuality: false,
				mutate: false,
			}) as RegionGeoJson
		} catch {
			continue
		}
		best = candidate
		if (serializedSize(candidate) <= TARGET_CHARS) {
			return {
				geojson: sanitizeGeometry(candidate),
				simplified: true,
				tooLarge: false,
			}
		}
	}

	// 3. Still too big even at the coarsest tolerance.
	return {
		geojson: sanitizeGeometry(best),
		simplified: true,
		tooLarge: serializedSize(best) > TARGET_CHARS,
	}
}

