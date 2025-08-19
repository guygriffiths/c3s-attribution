// Globally-available types should go here

declare global {
	const $l: ReturnType<typeof useLabels>

	type Language = 'en'

	interface ExtremeEvent {
		times: Date[]
		slices: any[]
		featureLevel?: number
		regions: any[]
		maxArea: number
		bbox: [number, number, number, number]
		centroid: [number, number]
		size: number
		feature: boolean
		ocean_only?: boolean
		id: string
		total_region: [number, number][]
		intensity?: number
		color?: string
	}

	interface ExtremeEventFull extends ExtremeEvent {
		values: any[]
		centroids: [[number, number]]
		total_area: number
		areas: number[]
		peak_values: number[]
		mean_values: number[]
	}
}

export { }

