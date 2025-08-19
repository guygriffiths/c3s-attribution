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
		ocean_only?: boolean // Whether the event is only in ocean regions
		id: number
		total_region: [number, number][]
		intensity?: number // Intensity of the event, if applicable
		color?: string // Color for the event, can be used for visualization
	}

	interface FullExtremeEvent {
		id: number
		times: Date[]
		regions: any[]
		slices: any[]
		values: any[]
		centroids: [[number, number]]
		bbox: [number, number, number, number]
		total_area: number
		areas: number[]
		peak_values: number[]
		mean_values: number[]
		color?: string
	}
}

export { }

