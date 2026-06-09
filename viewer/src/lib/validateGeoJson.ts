import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { simplifyForStorage } from './simplifyRegion'

type PolygonFeature = Feature<Polygon | MultiPolygon>
type RegionGeoJson = PolygonFeature | FeatureCollection<Polygon | MultiPolygon>

type ValidResult = {
	valid: true
	data: UserRegion
	warning?: string
}
type InvalidResult = {
	valid: false
	error: string
}

export function validateUserRegion(
	raw: unknown,
	filename = 'region',
): ValidResult | InvalidResult {
	let parsed: unknown
	if (typeof raw === 'string') {
		try {
			parsed = JSON.parse(raw)
		} catch {
			return { valid: false, error: 'Invalid JSON — the file could not be parsed.' }
		}
	} else {
		parsed = raw
	}

	if (typeof parsed !== 'object' || parsed === null) {
		return { valid: false, error: 'File does not contain a GeoJSON object.' }
	}

	const obj = parsed as Record<string, unknown>
	const type = obj.type

	if (type !== 'Feature' && type !== 'FeatureCollection') {
		return {
			valid: false,
			error: `Expected a GeoJSON Feature or FeatureCollection, got "${type}".`,
		}
	}

	// Derive a clean name from the filename (strip extension)
	const name = filename.replace(/\.(geo)?json$/i, '') || 'region'
	const id = crypto.randomUUID()

	// Shared finalisation: simplify for storage/rendering and assemble warnings.
	const finalize = (
		cleanGeojson: RegionGeoJson,
		featuresWarning?: string,
	): ValidResult | InvalidResult => {
		const { geojson, simplified } = simplifyForStorage(cleanGeojson)
		if (!geojson) {
			// Everything collapsed to degenerate geometry — nothing usable left.
			return {
				valid: false,
				error: 'No valid polygon geometry could be read from the file.',
			}
		}
		const warnings: string[] = []
		if (featuresWarning) warnings.push(featuresWarning)
		if (simplified) {
			warnings.push('Large region simplified to fit your browser and render smoothly.')
		}
		return {
			valid: true,
			data: { id, name, geojson },
			warning: warnings.length ? warnings.join(' ') : undefined,
		}
	}

	if (type === 'Feature') {
		const geom = obj.geometry as Record<string, unknown> | null
		if (
			!geom ||
			(geom.type !== 'Polygon' && geom.type !== 'MultiPolygon')
		) {
			return {
				valid: false,
				error: `Feature geometry must be a Polygon or MultiPolygon (got "${geom?.type ?? 'null'}").`,
			}
		}
		return finalize(parsed as PolygonFeature)
	}

	// FeatureCollection — filter to polygons only
	const features = Array.isArray(obj.features) ? obj.features : []
	const polygonFeatures = features.filter(
		(f: unknown) =>
			typeof f === 'object' &&
			f !== null &&
			(f as Record<string, unknown>).type === 'Feature' &&
			(
				((f as Record<string, unknown>).geometry as Record<string, unknown> | null)
					?.type === 'Polygon' ||
				((f as Record<string, unknown>).geometry as Record<string, unknown> | null)
					?.type === 'MultiPolygon'
			),
	) as PolygonFeature[]

	if (polygonFeatures.length === 0) {
		return {
			valid: false,
			error: 'No polygon or multipolygon features found in the file.',
		}
	}

	const discarded = features.length - polygonFeatures.length
	const featuresWarning =
		discarded > 0
			? `${discarded} feature${discarded === 1 ? '' : 's'} with unsupported geometry type${discarded === 1 ? '' : 's'} were ignored.`
			: undefined

	const geojson: FeatureCollection<Polygon | MultiPolygon> = {
		type: 'FeatureCollection',
		features: polygonFeatures,
	}

	return finalize(geojson, featuresWarning)
}
