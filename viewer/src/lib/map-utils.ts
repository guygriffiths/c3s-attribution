import iconPng from '@/assets/img/marker-icon-2x-c3sred.png'
import scssVars from '@/assets/styles/scssVars.module.scss'
import L from 'leaflet'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

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

export const centreMapOnDiv = (
	map: L.Map,
	div: HTMLElement,
	uncentre: boolean,
) => {
	// `map` = your Leaflet map
	// `div` = your HTML element where you want the map centre
	const rect = div.getBoundingClientRect()
	const mapSize = map.getSize()

	// calculate pixel offset from map centre
	const offsetX = rect.left + rect.width / 2 - mapSize.x / 2
	const offsetY = rect.top + rect.height / 2 - mapSize.y / 2
	console.log('centring map on div', rect, mapSize, offsetX, offsetY)
	// pan by the negative of that offset so the div moves to centre
	if (!uncentre) {
		map.panBy([-offsetX, -offsetY], {
			animate: true,
			// duration: parseFloat(scssVars.animTime.replace('s', '')) * 1000,
		})
	} else {
		map.panBy([offsetX, offsetY], {
			animate: true,
			// duration: parseFloat(scssVars.animTime.replace('s', '')) * 1000,
		})
	}
}

export const fitBoundsToDiv = (
	map: L.Map,
	div: HTMLElement,
	bbox: [number, number, number, number],
) => {
	const mapRect = map.getContainer().getBoundingClientRect()
	const divRect = div.getBoundingClientRect()

	// calculate padding for fitBounds
	const paddingTopLeft: L.PointExpression = [
		divRect.left - mapRect.left,
		divRect.top - mapRect.top,
	]
	const paddingBottomRight: L.PointExpression = [
		mapRect.right - divRect.right,
		mapRect.bottom - divRect.bottom,
	]

	console.log('fitting bounds to div', bbox, paddingTopLeft, paddingBottomRight)
	// @ts-ignore

	map.fitBounds(
		[
			[bbox[0], bbox[1]],
			[bbox[2], bbox[3]],
		],
		{
			paddingTopLeft,
			paddingBottomRight,
			// duration: parseFloat(scssVars.animTime.replace('s', '')) * 1000,
			animate: true,
		},
	)
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

export const markerIcon = L.icon({
	iconUrl: iconPng,
	shadowUrl: markerShadow,
	iconSize: [25, 41],
	iconAnchor: [12, 41],
	popupAnchor: [1, -34],
	tooltipAnchor: [16, -28],
	shadowSize: [41, 41],
})
