// Set the fixed bin thresholds based on domain
// The last bin edge is set based on data max to ensure all data is included
// This means the last bin will be wider than the others
export const getBins = (
	data: number[],
	types: EventType[],
	xmin: number,
	xmax: number,
	nbins: number,
	longtail: boolean,
) => {
	const N = longtail ? nbins + 1 : nbins
	const d = data ?? []
	const step = (xmax - xmin) / N
	const thresholds = Array.from({ length: nbins }, (_, i) => xmin + i * step)
	if (longtail) thresholds.push(xmax + step)

	// console.log('getBins', { data, xmin, xmax, nbins, step, thresholds })

	const binned = thresholds.slice(0, -1).map((t0, i) => {
		const t1 = thresholds[i + 1]
		const binIdx = d
			.map((val: number, j: number) => ({ val, j }))
			.filter(({ val }: { val: number }) => val >= t0 && val < t1)

		const hotCount = binIdx.filter(
			({ j }: { j: number }) => types[j] === 'hot',
		).length
		const coldCount = binIdx.filter(
			({ j }: { j: number }) => types[j] === 'cold',
		).length
		const total = binIdx.length || 1

		const binPoints = binIdx.map(({ val }: { val: number }) => val)
		return Object.assign(binPoints, {
			x0: t0,
			x1: t1,
			xmin,
			xmax,
			hotPct: hotCount / total,
			coldPct: coldCount / total,
			count: binIdx.length,
			endless: false,
		})
	})

	if (longtail && binned.length > 0) {
		binned[binned.length - 1].x1 = xmax
		binned[binned.length - 1].endless = true
	}
	// console.log('getBins', { binned })

	return binned
}
