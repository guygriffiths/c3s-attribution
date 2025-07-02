let debounceTimeout: NodeJS.Timeout | null = null

export const debounce = (func: () => void, delay: number) => {
	if (debounceTimeout) {
		clearTimeout(debounceTimeout)
	}
	debounceTimeout = setTimeout(() => {
		func()
	}, delay)
}