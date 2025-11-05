import * as d3 from 'd3'

export const debounce = (func: (...args: any[]) => void, delay: number) => {
	let timeout: ReturnType<typeof setTimeout> | null = null
	return (...args: any[]) => {
		if (timeout) clearTimeout(timeout)
		timeout = setTimeout(() => {
			func(...args)
		}, delay)
	}
}

// This is the same algorithm used in the backend to pack lat/lon to a pixel.
export const packPixelToInt = (lat: number, lon: number) => {
	const iLat = Math.round(lat * 4)
	while (lon < -180) lon += 360
	while (lon > 180) lon -= 360
	const iLon = Math.round(lon * 4)

	return (iLat << 16) | (iLon & 0xffff)
}

export const unpackIntToPixel = (packed: number): [number, number] => {
	const iLat = packed >> 16
	let iLon = packed & 0xffff
	if (iLon >= 0x8000) iLon -= 0x10000 // convert to signed

	return [iLat / 4, iLon / 4]
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

// export function interpolateColor(baseColor: string = 'rgb(151, 24, 65)') {
// 	const hsl = d3.hsl(baseColor)
// 	// lock hue/sat, vary lightness 0→1
// 	return (t: number) => d3.hsl(hsl.h, hsl.s, (1 - t) * 0.7 + 0.2).toString()
// }

export const interpolateColorHot = (baseColor: string = 'rgb(151, 24, 65)') => {
	const hcl = d3.hcl(baseColor)
	console.log('interpolateColorHot baseColor', baseColor, 'hcl', hcl)
	return (t: number) => {
		const H = (hcl.h + t * 100 - 80) % 360
		const C = Math.pow(t, 1.6) * 40
		const L = 20 + t * 70
		return d3.hcl(H, C, L).formatRgb()
	}
}

export const interpolateColorCold = (
	baseColor: string = 'rgb(44, 102, 162)',
) => {
	const hcl = d3.hcl(baseColor)
	return (t: number) => {
		const H = hcl.h + (t * 10)
		const C = Math.pow(t, 1.2) * 70
		const L = 80 - t * 70
		return d3.hcl(H, C, L).formatRgb()
	}
}

export const binGradient = (
	startPct: number,
	endPct: number,
	startColor: string,
	endColor: string,
) => {
	// Interpolate between red and blue based on startPct
	// startPct=1 => red, startPct=0 => blue
	const mix = d3.interpolateRgb(
		startColor ?? 'rgb(151, 24, 65)',
		endColor ?? 'rgb(44, 102, 162)',
	)(endPct) // or 1-startPct

	return mix
	// return `linear-gradient(135deg, ${startColor} ${startPct * 100}%, ${mix} 50%, ${endColor} ${endPct * 100}%)`
}

// Switch to a specific theme
export const setTheme = (themeName: 'hot' | 'cold' | 'hotcold') => {
	console.log('Setting theme to', themeName)
	const root = document.documentElement
	const themePrefix = `--theme-${themeName}-`

	const styles: any = getComputedStyle(root)

	// Loop over all computed properties instead
	for (const prop of styles) {
		if (prop.startsWith(themePrefix)) {
			const token = prop.replace(themePrefix, '')
			const value = styles.getPropertyValue(prop)
			root.style.setProperty(`--${token}`, value)
		}
	}
}
