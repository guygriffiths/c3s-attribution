
export const debounce = (func: (...args: any[]) => void, delay: number) => {
	let timeout: ReturnType<typeof setTimeout> | null = null
	return (...args: any[]) => {
		if (timeout) clearTimeout(timeout)
		timeout = setTimeout(() => {
			func(...args)
		}, delay)
	}
}

export const packPixelToInt = (lat: number, lon: number) => {
	const iLat = Math.round(lat * 4)
	const iLon = Math.round(lon * 4)
	return (iLat << 16) | (iLon & 0xffff)
}


export const toPx = (value: string): number => {
	if (value.endsWith('%')) {
		return (window.innerWidth * parseFloat(value)) / 100
	}
	if (value.endsWith('rem')) {
		return (
			parseFloat(value) *
			parseFloat(getComputedStyle(document.documentElement).fontSize)
		)
	}
	if (value.endsWith('px')) {
		return parseFloat(value)
	}
	return parseFloat(value) // fallback
}


