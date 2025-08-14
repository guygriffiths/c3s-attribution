import scssVars from '@/assets/styles/scssVars.module.scss'

export const fitMapToBounds = (map: L.Map, event: ExtremeEvent) => {
	// TODO - 32px is hardcoded padding, yuck
	map.fitBounds(
		[
			[event.bbox[0], event.bbox[1]],
			[event.bbox[2], event.bbox[3]],
		],
		{
			paddingTopLeft: [64, 64],
			paddingBottomRight: [
				map.getSize().x * 0.5 + 32,
				map.getSize().y * 0.5 + 32,
			],
			maxZoom: 12,
			// @ts-ignore
			duration: scssVars.animTime,
		},
	)
}

export const wrafLevelChanged = (store: any, newVal: string) => {
	if (newVal === 'none') {
		store.regionsToSelectBy = undefined
	} else {
		fetch(`/regions/region-${newVal}.geojson`)
			.then((response) => response.json())
			.then((data: GeoJSON.FeatureCollection) => {
				store.regionsToSelectBy = data
				console.log('Regions to select by:', store.regionsToSelectBy)
			})
			.catch((error) => {
				console.error('Error fetching regions:', error)
			})
	}
}

export const getZeitgeistOpacity = (stepsFromNow: number) => {
	if (stepsFromNow === 0) {
		return 1
	}
	// const stepsFromNow = Math.abs(differenceInDays(store.selectedTime, store.selectedEvent.times[idx]))
	const maxSteps = 6
	const opacity = 0.5 - (0.5 * stepsFromNow) / maxSteps
	if (stepsFromNow > maxSteps) {
		return 0
	}
	return Math.max(opacity, 0.01)
}

