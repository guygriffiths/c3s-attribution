// Globally-available types should go here

declare global {
	const $l: ReturnType<typeof useLabels>

	type Language = 'en'

	type ViewMode = 'timemachine' | 'heatmap'

	interface ExtremeEvent {
		id: string
		times: Date[]
		duration: number // in days
		regions: [number, number][][]
		total_region: [number, number][]
		bbox: [number, number, number, number]
		peak_value: number
		mean_value: number
		total_area: number
		pixel_count: number
		pixel_set: [number, number][]
		packedPixelSet?: Set<number>
		ocean_only: boolean
		color: string
	}

	interface ExtremeEventFull extends ExtremeEvent {
		slices: [number, number][][]
		values: number[][]
		centroids: [number, number][]
		areas: number[]
		peak_values: number[]
		mean_values: number[]
		pixel_peak_values: number[]
	}

	interface WeatherEvent {
		id: string
		times: Date[]
		color?: string
		y?: number
		startX?: number
		endX?: number
	}
}

export { }

