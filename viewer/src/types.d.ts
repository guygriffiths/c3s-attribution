// Globally-available types should go here

declare global {
	const $l: ReturnType<typeof useLabels>

	type Language = 'en'

	type ViewMode = 'timemachine' | 'heatmap'

	type TimeReelMode = 'default' | 'timeline' | 'eventzoom' | 'overview'

	type EventType = 'hot' | 'cold' | 'wet'
	type SelectedEventType = EventType | 'hotcold' | 'hotwet' | 'coldwet' | 'all'

	type Variable = 'duration' | 'size' | 'intensity'

	interface ExtremeEvent {
		id: string
		times: number[]
		duration: number // in days
		regions: [number, number][][]
		total_region: [number, number][]
		bbox: [number, number, number, number]
		max_value: number
		mean_value: number
		min_value: number
		total_area: number
		pixel_count: number
		pixel_set: number[]
		packedPixelSet?: Set<number>
		ocean_only: boolean
		color: string
		event_type: EventType
	}

	interface ExtremeEventFull extends ExtremeEvent {
		slices: [number, number][][]
		values: number[][]
		centroids: [number, number][]
		areas: number[]
		max_values: number[]
		mean_values: number[]
		min_values: number[]
		pixel_set?: [number, number][]
		pixel_max_values: number[]
	}

	interface EventBox {
		eventId: string
		type: EventType
		color: string
		y: number
		startX: number
		endX: number
	}

	interface Filters {
		duration: {
			minimum: boolean
			value: number
		}
		size: {
			minimum: boolean
			value: number
		}
		heatIntensity: {
			minimum: boolean
			type: 'intensity' | 'min' | 'mean' | 'max'
			value: number
			active: boolean
		}
		coldIntensity: {
			minimum: boolean
			type: 'intensity' | 'min' | 'mean' | 'max'
			value: number
			active: boolean
		}
		wetIntensity: {
			minimum: boolean
			value: number
			active: boolean
		}
	}
}

export { }

