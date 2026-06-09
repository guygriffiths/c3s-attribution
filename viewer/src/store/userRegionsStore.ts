import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'c3s_user_regions'
export const MAX_USER_REGIONS = 3

interface State {
	regions: UserRegion[]
	activeRegionId: string | null
	selectedFeatureIndex: number | null
}

export const useUserRegionsStore = defineStore('userRegions', {
	state: (): State => ({
		regions: [],
		activeRegionId: null,
		selectedFeatureIndex: null,
	}),

	getters: {
		activeRegion: (state): UserRegion | null =>
			state.regions.find((r) => r.id === state.activeRegionId) ?? null,

		activeFeature: (state): Feature<Polygon | MultiPolygon> | null => {
			const region = state.regions.find((r) => r.id === state.activeRegionId)
			if (!region) return null
			if (region.geojson.type === 'Feature') return region.geojson
			// FeatureCollection
			const features = region.geojson.features
			if (features.length === 1) return features[0]
			// Multi-mode: only return a feature when one is explicitly selected
			if (state.selectedFeatureIndex !== null) return features[state.selectedFeatureIndex]
			return null
		},

		isMultiMode: (state): boolean => {
			const region = state.regions.find((r) => r.id === state.activeRegionId)
			if (!region) return false
			if (region.geojson.type !== 'FeatureCollection') return false
			return region.geojson.features.length > 1 && state.selectedFeatureIndex === null
		},

		featureCount: (state): number => {
			const region = state.regions.find((r) => r.id === state.activeRegionId)
			if (!region) return 0
			if (region.geojson.type === 'Feature') return 1
			return region.geojson.features.length
		},
	},

	actions: {
		loadFromStorage() {
			try {
				const raw = localStorage.getItem(STORAGE_KEY)
				if (raw) {
					const parsed = JSON.parse(raw)
					if (Array.isArray(parsed)) {
						this.regions = parsed
					}
				}
			} catch {
				// Corrupt storage — start fresh
				this.regions = []
			}
		},

		saveToStorage(): boolean {
			try {
				localStorage.setItem(STORAGE_KEY, JSON.stringify(this.regions))
				return true
			} catch (e) {
				// Most likely QuotaExceededError — the region is too large for localStorage
				console.warn('Failed to persist user regions to localStorage', e)
				return false
			}
		},

		addRegion(region: UserRegion): boolean {
			if (this.regions.length >= MAX_USER_REGIONS) {
				console.warn('User region limit reached')
				return false
			}
			this.regions.push(region)
			if (!this.saveToStorage()) {
				// Roll back — storage rejected it (e.g. too large)
				this.regions.pop()
				return false
			}
			return true
		},

		deleteRegion(id: string) {
			if (this.activeRegionId === id) {
				this.deactivate()
			}
			this.regions = this.regions.filter((r) => r.id !== id)
			this.saveToStorage()
		},

		mergeIntoRegion(
			targetId: string,
			incoming: Feature<Polygon | MultiPolygon> | FeatureCollection<Polygon | MultiPolygon>,
		): boolean {
			const target = this.regions.find((r) => r.id === targetId)
			if (!target) return false

			// Snapshot for rollback if storage rejects the enlarged region
			const previous = target.geojson

			const incomingFeatures: Feature<Polygon | MultiPolygon>[] =
				incoming.type === 'Feature' ? [incoming] : incoming.features

			if (target.geojson.type === 'Feature') {
				// Upgrade target to FeatureCollection
				target.geojson = {
					type: 'FeatureCollection',
					features: [target.geojson, ...incomingFeatures],
				}
			} else {
				target.geojson = {
					type: 'FeatureCollection',
					features: [...target.geojson.features, ...incomingFeatures],
				}
			}

			if (!this.saveToStorage()) {
				target.geojson = previous
				return false
			}
			return true
		},

		setActive(id: string) {
			this.activeRegionId = id
			this.selectedFeatureIndex = null
		},

		selectFeature(index: number) {
			this.selectedFeatureIndex = index
		},

		clearFeatureSelection() {
			this.selectedFeatureIndex = null
		},

		deactivate() {
			this.activeRegionId = null
			this.selectedFeatureIndex = null
		},
	},
})
