import * as d3 from 'd3'

export const DATA_ROOT = `${import.meta.env.X_PUBLIC_PATH || ''}data/`

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

export const interpolateColorHot = (
	baseColor: string = 'rgb(224, 192, 233)',
) => {
	const hcl = d3.lch(baseColor)
	const retfunc = (t: number) => {
		const H = hcl.h - (((t - 1) * 20) % 360)
		const C = hcl.c + (Math.pow(t, 1.2) - 0.5) * 125
		const L = hcl.l + (0.2 + 0.8 * (t - 0.4)) * 110
		return d3.lch(L, C, H).formatRgb()
	}
	return retfunc
}

export const interpolateColorCold = (
	baseColor: string = 'rgb(44, 102, 162)',
) => {
	const hcl = d3.lch(baseColor)
	return (t: number) => {
		const H = hcl.h + t * 10
		const C = Math.pow(t, 1.2) * 70
		const L = 90 - t * 65
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
	console.time(`Setting theme to ${themeName}`)
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
	console.timeEnd(`Setting theme to ${themeName}`)
}

export const fetchDataForYear = async (year: number) => {
	const [hot, cold] = await Promise.all([
		fetch(`${DATA_ROOT}events-hot-${year}.jsonl`)
			.then((r) => r.text())
			.then((t) =>
				t
					.trim()
					.split('\n')
					.map((line) => {
						const event = JSON.parse(line)
						// Convert to timestamps (numbers) instead of Date objects
						event.times = event.times.map((t: string) => new Date(t).getTime())
						return event
					}),
			)
			.catch(() => []),

		fetch(`${DATA_ROOT}events-cold-${year}.jsonl`)
			.then((r) => r.text())
			.then((t) =>
				t
					.trim()
					.split('\n')
					.map((line) => {
						const event = JSON.parse(line)
						event.times = event.times.map((t: string) => new Date(t).getTime())
						return event
					}),
			)
			.catch(() => []),
	])
	return [hot, cold]
}
