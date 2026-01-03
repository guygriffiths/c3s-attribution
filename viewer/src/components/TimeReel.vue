<script setup lang="ts">
import TimeReelWorker from '@/lib/worker/timeReelEventProcessWorker?worker'
import scssVars from '@/assets/styles/scssVars.module.scss'
import { useLabels } from '@/lib/labels'
import {
	getEventBoxes,
	dayStr,
	monthsForYear,
	TOTAL_DAYS,
	intervalToMs,
	dateStr,
} from '@/lib/time-utils'
import * as d3 from 'd3'
import {
	addHours,
	differenceInDays,
	differenceInHours,
	getDayOfYear,
	setDayOfYear,
	subHours,
} from 'date-fns'
import {
	computed,
	defineModel,
	nextTick,
	onBeforeUnmount,
	onMounted,
	onUnmounted,
	ref,
	Ref,
	watch,
} from 'vue'
import {
	IconCrosshair,
	IconArrowsMove,
	IconArrowBarToRight,
	IconArrowBarToLeft,
	IconChevronLeftPipe,
	IconChevronLeft,
	IconChevronRight,
	IconChevronRightPipe,
	IconPlayerPlay,
	IconPlayerPause,
} from '@tabler/icons-vue'

const $l = useLabels()

const props = defineProps<{
	start: Date
	end: Date
	startFilter: Date
	endFilter: Date
	events: ExtremeEvent[]
	selectedEvent: ExtremeEventFull | null
	hoverEvent: ExtremeEvent | null
	mode: TimeReelMode
	showBars: boolean
	eventType: 'hotcold' | 'hot' | 'cold'
	colorForEvent: (event: ExtremeEvent) => string | null
	speedFactor: number
}>()

const startYear = computed(() => props.start.getUTCFullYear())
const endYear = computed(() => props.end.getUTCFullYear())
const totalYears = computed(() => endYear.value - startYear.value + 1)
const years = computed(() =>
	Array.from({ length: totalYears.value }, (_, i) => startYear.value + i),
)
const showBars = computed(() => props.showBars && !isTimeline.value)

const model: Ref<Date> = defineModel({
	type: Date,
	default: new Date(),
})
const selectedDay = computed(() => getDayOfYear(model.value))
const selectedYear = computed(() => model.value.getUTCFullYear())

const emits = defineEmits<{
	(event: 'eventSelected', ev: ExtremeEvent | null): void
	(event: 'playing'): void
	(event: 'paused'): void
	(event: 'hover', ev: ExtremeEvent | null): void
	(event: 'update:startFilter', date: Date): void
	(event: 'update:endFilter', date: Date): void
}>()

////////////////////
// Time selection //
////////////////////
const setDate = (dateVal: number) => {
	// console.trace('TimeReel: setDate to', new Date(dateVal).toISOString())
	const date = new Date(dateVal)
	if (
		date.getUTCFullYear() >= props.start.getUTCFullYear() &&
		date.getUTCFullYear() <= props.end.getUTCFullYear()
	) {
		model.value = date
	}
}
const autoScrolling = ref(false)
const scrollToYear = (year: number) => {
	console.trace('scrollToYear', year)
	if (scroller.value) {
		// Snap to top of specified year
		const yearsOffset = year - startYear.value
		const scrollOffset = (yearsOffset + 0.5) * rowHeight.value
		// console.log('scrolling to year', year, 'at offset', scrollOffset)
		scroller.value.scrollTo({
			top: scrollOffset,
			behavior: 'smooth',
		})
	}
}
const nextDay = () => {
	if (isTimeline.value) {
		let newStart = addHours(props.startFilter, 4 * 7 * 24)
		let newEnd = addHours(props.endFilter, 4 * 7 * 24)
		if (newEnd > props.end) {
			newEnd = props.end
			newStart = subHours(
				newEnd,
				differenceInDays(props.endFilter, props.startFilter) * 24,
			)
		}
		emits('update:startFilter', newStart)
		emits('update:endFilter', newEnd)
		return
	}
	const newVal = addHours(model.value, 24)
	if (newVal.getUTCFullYear() <= endYear.value) {
		if (newVal.getUTCFullYear() !== model.value.getUTCFullYear()) {
			autoScrolling.value = true
			model.value = newVal
			scrollToYear(newVal.getUTCFullYear() - 1)
			nextTick(() => {
				autoScrolling.value = false
			})
		} else {
			model.value = newVal
		}
	}
}
const prevDay = () => {
	if (isTimeline.value) {
		let newStart = subHours(props.startFilter, 4 * 7 * 24)
		let newEnd = subHours(props.endFilter, 4 * 7 * 24)
		if (newStart < props.start) {
			newStart = props.start
			newEnd = addHours(
				newStart,
				differenceInDays(props.endFilter, props.startFilter) * 24,
			)
		}
		emits('update:startFilter', newStart)
		emits('update:endFilter', newEnd)
		return
	}
	const newVal = subHours(model.value, 24)
	if (newVal.getUTCFullYear() >= startYear.value) {
		if (newVal.getUTCFullYear() !== model.value.getUTCFullYear()) {
			autoScrolling.value = true
			model.value = newVal
			scrollToYear(newVal.getUTCFullYear() - 1)
			nextTick(() => {
				autoScrolling.value = false
			})
		} else {
			model.value = newVal
		}
	}
}
const startOfYear = () => {
	if (isZoom.value && props.selectedEvent) {
		setDate(props.selectedEvent.times[0])
		return
	} else if (isTimeline.value) {
		emits(
			'update:endFilter',
			addHours(
				props.start,
				differenceInHours(props.endFilter, props.startFilter),
			),
		)
		emits('update:startFilter', props.start)
		return
	}
	setDate(Date.UTC(selectedYear.value, 0, 1))
}
const endOfYear = () => {
	if (isZoom.value && props.selectedEvent) {
		setDate(props.selectedEvent.times[props.selectedEvent.times.length - 1])
		return
	} else if (isTimeline.value) {
		emits(
			'update:startFilter',
			subHours(
				props.end,
				differenceInHours(props.endFilter, props.startFilter),
			),
		)
		emits('update:endFilter', props.end)
		return
	}
	setDate(Date.UTC(selectedYear.value, 11, 31))
}
const nextYear = () => {
	const newYear = selectedYear.value + 1
	setDate(Date.UTC(newYear, 0, selectedDay.value))
	autoScrolling.value = true
	scrollToYear(newYear - 1)
	nextTick(() => {
		autoScrolling.value = false
	})
}
const prevYear = () => {
	const newYear = selectedYear.value - 1
	setDate(Date.UTC(newYear, 0, selectedDay.value))
	autoScrolling.value = true
	scrollToYear(newYear - 1)
	nextTick(() => {
		autoScrolling.value = false
	})
}

const playing = ref(false)
const frameInterval = computed(() => {
	let FPS = 15
	if (isZoom.value) FPS = 2.5 * props.speedFactor
	if (isTimeline.value) FPS = 60
	return 1000 / FPS
})

const togglePlay = () => {
	if (!props.selectedEvent && isZoom.value) return

	if (
		!playing.value &&
		(model.value.getTime() === props.end.getTime() ||
			(isZoom.value &&
				model.value.getTime() ===
					props.selectedEvent!.times[props.selectedEvent!.times.length - 1]))
	) {
		// Restart from beginning
		if (isZoom.value && props.selectedEvent) {
			setDate(props.selectedEvent.times[0])
		} else {
			setDate(Date.UTC(selectedYear.value, 0, 1))
		}
	}
	playing.value = !playing.value
	if (playing.value) {
		emits('playing')
	} else {
		emits('paused')
	}
	if (playing.value) {
		let last = performance.now()

		const step = (ts: number) => {
			if (!playing.value) return

			if (ts - last >= frameInterval.value) {
				if (isTimeline.value) {
					// Timeline mode: stop at end date
					let newStart = addHours(
						props.startFilter,
						props.speedFactor * 3 * 4 * 7 * 24,
					)
					let newEnd = addHours(
						props.endFilter,
						props.speedFactor * 3 * 4 * 7 * 24,
					)
					if (newEnd > props.end) {
						newEnd = props.end
						playing.value = false
					} else {
						emits('update:startFilter', newStart)
						emits('update:endFilter', newEnd)
					}
				} else {
					if (
						model.value.getTime() === props.end.getTime() ||
						(isZoom.value &&
							model.value.getTime() ===
								props.selectedEvent!.times[
									props.selectedEvent!.times.length - 1
								])
					) {
						// Reached end of event
						playing.value = false
						return
					} else {
						nextDay()
					}
				}
				last = ts
			}

			requestAnimationFrame(step)
		}

		requestAnimationFrame(step)
	}
}

////////////////////
// UI Interaction //
////////////////////
const timeReelRef = ref<HTMLDivElement | null>(null)
const needleRef = ref<HTMLDivElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const scroller = computed(() => timeReelRef.value?.querySelector('.scroller'))

const rowHeight = ref(128)
const updateRowHeight = () => {
	const parentHeight = timeReelRef.value?.clientHeight || 0
	rowHeight.value = parentHeight > 0 ? parentHeight / rowsToShow.value : 128
}

const rowsToShow = computed(() => {
	switch (props.mode) {
		case 'timeline':
		case 'eventzoom':
			return 1
		case 'overview':
			return endYear.value - startYear.value + 1
		case 'default':
		default:
			return 2
	}
})
watch(rowsToShow, () => updateRowHeight())

const maxSimultaneousEvents = ref(3)

const eventHeight = computed(() => 1.0 / maxSimultaneousEvents.value)

const isDragging = ref(false)
const hasMoved = ref(false)
const dragMode = ref<'horizontal' | 'vertical' | null>(null)
let startX = 0
let startY = 0
let startDate: Date = new Date(model.value)
let startMs = 0

const isTimeline = computed(() => props.mode === 'timeline')
const isZoom = computed(() => props.mode === 'eventzoom')
const isDefault = computed(() => props.mode === 'default')
const isOverview = computed(() => props.mode === 'overview')

const localNeedleOffset = ref(null as number | null)
const rangeDrag = ref<'start' | 'end' | 'move' | null>(null)
let rangeDragStartDate: Date | null = null
let rangeDragEndDate: Date | null = null
const startDrag = (event: MouseEvent) => {
	if (event === null || event.target === null) return
	// console.log('startDrag', event, event.target)
	if ((event.target as HTMLElement).classList.contains('start-handle')) {
		rangeDrag.value = 'start'
	} else if ((event.target as HTMLElement).classList.contains('end-handle')) {
		rangeDrag.value = 'end'
	} else if ((event.target as HTMLElement).classList.contains('grab-area')) {
		rangeDrag.value = 'move'
	} else {
		rangeDrag.value = null
	}
	if (rangeDrag.value !== null) {
		rangeDragStartDate = new Date(props.startFilter!)
		rangeDragEndDate = new Date(props.endFilter!)
	}
	isDragging.value = true
	hasMoved.value = true
	// setTimeout(() => {
	// 	if (isDragging.value) {
	// 		hasMoved.value = true
	// 	}
	// }, intervalToMs(scssVars.animTime))
	dragMode.value = null

	startX = event.clientX
	startY = event.clientY
	startMs = performance.now()
	startDate = model.value
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', endDrag)

	if (isZoom.value) {
		localNeedleOffset.value = 0
	} else {
		localNeedleOffset.value = null
	}

	if (isOverview.value) {
		initialScrubberPos.value = [
			needleOffsetPx.value - 12,
			(selectedYear.value - startYear.value + 0.5) * rowHeight.value - 24,
		]
		scrubStartYear.value = selectedYear.value
		scrubStartDay.value = selectedDay.value
	}
}
const initialScrubberPos = ref<[number, number]>([0, 0])

const endDrag = (event: MouseEvent) => {
	isDragging.value = false
	hasMoved.value = false
	dragMode.value = null
	localNeedleOffset.value = null
	localScrubberOffset.value = null
	const time = performance.now() - startMs
	if (time < 200 && Math.abs(event.clientX - startX) < 5) {
		if (rangeDrag.value !== null) {
			// Range drag ended with a click, ignore
			rangeDrag.value = null
			window.removeEventListener('mousemove', handleDrag)
			window.removeEventListener('mouseup', endDrag)
			return
		}
		// This was a click, not a drag
		// const container = containerRef.value
		const clickXOff =
			event.clientX - (scroller.value?.getBoundingClientRect().left || 0)
		if (isZoom.value) {
			const percentage =
				(clickXOff - xOffset.value) / (scroller.value?.clientWidth || 1)
			if (!props.selectedEvent) return
			const eventStart = getDayOfYear(props.selectedEvent.times[0])
			const eventEnd = getDayOfYear(
				props.selectedEvent.times[props.selectedEvent.times.length - 1],
			)
			const totalZoomedDays = (eventEnd - eventStart + 2) * xScaleFactor.value

			const dayFromStart = Math.floor(
				Math.max(0, Math.min(1, percentage)) * totalZoomedDays,
			)
			const newDate = setDayOfYear(
				new Date(Date.UTC(selectedYear.value, 0, 1)),
				dayFromStart + eventStart - 1,
			)
			// Only set the date if it has changed, otherwise it slows things down unnecessarily
			if (differenceInDays(newDate, model.value) !== 0) {
				setDate(
					Date.UTC(
						newDate.getFullYear(),
						newDate.getMonth(),
						newDate.getDate(),
					),
				)
			}
		} else if (isOverview.value) {
			try {
				const percentage =
					(clickXOff - 40) / (scroller.value?.clientWidth! - 40)
				const totalDays = 365
				const dayFromStart = Math.floor(
					1 + Math.max(0, Math.min(1, percentage)) * totalDays,
				)
				const newDate = new Date(Date.UTC(selectedYear.value, 0, dayFromStart))

				const clickYOff =
					event.clientY - (scroller.value?.getBoundingClientRect().top || 0)
				const ySize = rowHeight.value
				const yearClicked = Math.floor(clickYOff / ySize) + startYear.value
				if (yearClicked !== selectedYear.value) {
					setDate(Date.UTC(yearClicked, newDate.getMonth(), newDate.getDate()))
				}
			} catch (e) {
				console.error('Error handling overview click:', e)
			}
		} else {
			const percentage = clickXOff / (scroller.value?.clientWidth || 1)
			const totalDays = selectedYear.value % 4 === 0 ? 365 : 364
			const dayFromStart = Math.floor(
				1 + Math.max(0, Math.min(1, percentage)) * totalDays,
			)
			const newDate = new Date(Date.UTC(selectedYear.value, 0, dayFromStart))
			setDate(
				Date.UTC(newDate.getFullYear(), newDate.getMonth(), newDate.getDate()),
			)
		}
	}

	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', endDrag)
}

const localScrubberOffset = ref<[number, number] | null>(null) // x,y
const scrubStartYear = ref(selectedYear.value)
const scrubStartDay = ref(selectedDay.value)
const handleDrag = (event: MouseEvent) => {
	const dx = event.clientX - startX
	const dy = event.clientY - startY

	if (isOverview.value) {
		localScrubberOffset.value = [dx, dy]
		const yearOffset = Math.round(dy / rowHeight.value)
		const dayOffset = Math.round(
			(dx / (scroller.value?.clientWidth || 1)) * TOTAL_DAYS,
		)
		setDate(
			Date.UTC(
				scrubStartYear.value + yearOffset,
				0,
				scrubStartDay.value + dayOffset,
			),
		)
	} else {
		if (!dragMode.value) {
			if (Math.abs(dx) > Math.abs(dy)) dragMode.value = 'horizontal'
			else if (Math.abs(dy) > Math.abs(dx)) dragMode.value = 'vertical'
			else return
		}

		if (dragMode.value === 'horizontal') {
			const container = containerRef.value
			if (container) {
				if (!isZoom.value) {
					const rect = container.getBoundingClientRect()
					if (rangeDrag.value !== null) {
						const pixelsPerDay = rect.width / (years.value.length * TOTAL_DAYS)
						const daysMoved = Math.round(dx / pixelsPerDay)
						let newStart = new Date(rangeDragStartDate!)
						let newEnd = new Date(rangeDragEndDate!)
						if (rangeDrag.value === 'start' || rangeDrag.value === 'move') {
							newStart = addHours(rangeDragStartDate!, 24 * daysMoved)
							if (newStart < props.start) newStart = props.start
						}
						if (rangeDrag.value === 'end' || rangeDrag.value === 'move') {
							newEnd = addHours(rangeDragEndDate!, 24 * daysMoved)
							if (newEnd > props.end) newEnd = props.end
						}
						emits('update:startFilter', newStart)
						emits('update:endFilter', newEnd)
					} else {
						// const totalDays = selectedYear.value % 4 === 0 ? 365 : 364
						const pixelsPerDay = rect.width / TOTAL_DAYS
						const daysMoved = Math.round(dx / pixelsPerDay)
						// addHours will respect DST, addDays won't
						const newDate = addHours(startDate, 24 * daysMoved)
						if (newDate.getFullYear() === selectedYear.value) {
							setDate(newDate.getTime())
						} else if (newDate.getFullYear() < selectedYear.value) {
							setDate(Date.UTC(selectedYear.value, 0, 1))
						} else if (newDate.getFullYear() > selectedYear.value) {
							setDate(Date.UTC(selectedYear.value, 11, 31))
						}
					}
				} else {
					const rect = container.getBoundingClientRect()
					const totalDays = props.selectedEvent
						? differenceInDays(
								props.selectedEvent.times[props.selectedEvent.times.length - 1],
								props.selectedEvent.times[0],
							) * xScaleFactor.value
						: 365
					const pixelsPerDay = rect.width / totalDays
					const daysMoved = Math.round(dx / pixelsPerDay)
					localNeedleOffset.value = dx / pixelsPerDay - daysMoved

					// No need to set anything and trigger a re-render if we haven't actually changed the day
					if (daysMoved === 0) return
					// addHours will respect DST, addDays won't
					const newDate = addHours(startDate, 24 * daysMoved)
					if (newDate.getFullYear() === selectedYear.value) {
						setDate(newDate.getTime())
					} else if (newDate.getFullYear() < selectedYear.value) {
						setDate(Date.UTC(selectedYear.value, 0, 1))
					} else if (newDate.getFullYear() > selectedYear.value) {
						setDate(Date.UTC(selectedYear.value, 11, 31))
					}
				}
			}
			// console.log('dy=', dy, 'scroller.scrollTop=', scroller.value!.scrollTop)
			// scroller.value!.scrollTop += dy
			// console.log('dy=', dy, 'scroller.scrollTop=', scroller.value!.scrollTop)
			// }
		} else if (dragMode.value === 'vertical') {
			//  scroller.value!.scrollTop += dy
		}
	}
}

const eventClicked = (box: EventBox) => {
	emits('eventSelected', props.events.find((e) => e.id === box.eventId) || null)
}
const eventHovered = (box: EventBox | null) => {
	if (box === null) {
		emits('hover', null)
		return
	}
	emits('hover', props.events.find((e) => e.id === box.eventId) || null)
}

const getNeedleOffsetPct = (date: Date | null) => {
	if (date === null) return 0
	if (isDefault.value || isOverview.value) {
		const selectedDay = getDayOfYear(date)
		const offset = (selectedDay / TOTAL_DAYS) * 100
		return Math.max(Math.min(offset, 100), 0)
	} else if (isTimeline.value) {
		const totalDays = differenceInDays(props.end, props.start) + 1
		const daysFromStart = differenceInDays(date, props.start) + 1
		const offset = (daysFromStart / totalDays) * 100 + 0.5
		return Math.max(Math.min(offset, 100), 0)
	} else if (isZoom.value && props.selectedEvent) {
		const eventStart = getDayOfYear(props.selectedEvent.times[0])
		const selectedDay = getDayOfYear(date)
		const eventEnd = getDayOfYear(
			props.selectedEvent.times[props.selectedEvent.times.length - 1],
		)
		const totalZoomedDays = (eventEnd - eventStart + 2) * xScaleFactor.value
		const offset = selectedDay - eventStart + 1
		if (localNeedleOffset.value !== null) {
			return Math.max(
				Math.min(
					((offset + localNeedleOffset.value) / totalZoomedDays) * 100,
					100,
				),
				0,
			)
		}
		return (offset / totalZoomedDays) * 100
	} else {
		// Fallback, shouldn't get here
		return (selectedDay.value / TOTAL_DAYS) * 100
	}
}
const needleOffsetPx = computed(() => {
	const pct = getNeedleOffsetPct(model.value)
	const containerWidth = scroller.value?.clientWidth
	if (isOverview.value) {
		return 40 + (pct! / 100) * (containerWidth! - 40)
	} else if (isZoom.value) {
		return (pct! / 100) * containerWidth! + xOffset.value
	} else {
		return (pct! / 100) * containerWidth!
	}
})
const startNeedleOffsetPx = computed(() => {
	const pct = getNeedleOffsetPct(props.startFilter)
	const containerWidth = scroller.value?.clientWidth
	if (isOverview.value) {
		return 40 + (pct! / 100) * (containerWidth! - 40)
	} else if (isZoom.value) {
		return (pct! / 100) * containerWidth! + xOffset.value
	} else {
		return (pct! / 100) * containerWidth!
	}
})
const endNeedleOffsetPx = computed(() => {
	const pct = getNeedleOffsetPct(props.endFilter)
	const containerWidth = scroller.value?.clientWidth
	if (isOverview.value) {
		return 40 + (pct! / 100) * (containerWidth! - 40)
	} else if (isZoom.value) {
		return (pct! / 100) * containerWidth! + xOffset.value
	} else {
		return (pct! / 100) * containerWidth!
	}
})

const eventBoxesForYear = ref<Record<number, EventBox[]>>({})
const positionY = (y: number, eventType: 'hot' | 'cold') => {
	if (props.eventType === 'hotcold') {
		return (0.5 + y) * eventHeight.value * (eventType === 'hot' ? -1 : 1)
	} else {
		if (y % 2 !== 0) {
			return 0.5 * y * eventHeight.value
		} else {
			return -0.5 * (y + 1) * eventHeight.value
		}
	}
}

onMounted(() => {
	for (let year of years.value) {
		const res = getEventBoxes(props.events, year, props.eventType === 'hotcold')
		eventBoxesForYear.value[year] = res.events
	}
	const handleKey = (e: KeyboardEvent) => {
		if (isTimeline.value) return
		// TODO Should all of this go in a global key handler? Perhaps not, since people use arrow keys on maps?
		if (e.key === 'ArrowLeft') {
			e.preventDefault()
			prevDay()
		} else if (e.key === 'ArrowRight') {
			e.preventDefault()
			nextDay()
		}
		// else if (e.key === 'PageUp') {prevYear()}
		// else if (e.key === 'PageDown') {nextYear()}
		else if (e.key === 'ArrowUp') {
			e.preventDefault()
			prevYear()
		} else if (e.key === 'ArrowDown') {
			e.preventDefault()
			nextYear()
		} else if (e.key === ' ') {
			e.preventDefault()
			togglePlay()
		}
		// else if (e.key === 'R') {nextYear()}
		else if (e.key === 'Home') {
			e.preventDefault()
			setDate(props.start.getTime())
		} else if (e.key === 'End') {
			e.preventDefault()
			setDate(props.end.getTime())
		}
	}
	window.addEventListener('keydown', handleKey)
	// @ts-ignore
	scroller.value!.addEventListener('keydown', (e: KeyboardEvent) => {
		if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
			e.preventDefault() // stop browser default scroll
		}
	})

	if (model.value > props.end) {
		model.value = new Date(props.end.getTime())
	} else if (model.value < props.start) {
		model.value = new Date(props.start.getTime())
	}

	updateRowHeight() // initial
	const ro = new ResizeObserver(updateRowHeight)
	if (timeReelRef.value) {
		ro.observe(timeReelRef.value)
		timeReelRef.value.focus()
	}

	if (scroller.value) {
		const yearsOffset = selectedYear.value - startYear.value
		const scrollOffset = 0.5 * (yearsOffset * 2 - 1)
		scroller.value.scrollTo({
			top: scrollOffset * rowHeight.value,
		})
	}

	onBeforeUnmount(() => {
		window.removeEventListener('keydown', handleKey)
	})
	onUnmounted(() => ro.disconnect())
})

const topRowHeight = computed(() => {
	return isOverview.value
		? '0'
		: `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})
const bottomRowHeight = computed(() => {
	return isOverview.value
		? '0'
		: `calc(0.5 * (100% - (100% / ${rowsToShow.value})))`
})

const highlightRowHeight = computed(() =>
	isOverview.value ? '100%' : `calc(100% / ${rowsToShow.value})`,
)

const scrollListener = () => {
	// console.log('scrolling!!!!!', autoScrolling.value, scroller.value)
	if (autoScrolling.value || !scroller.value) return
	const scrollTop = scroller.value.scrollTop
	const rowsDown = scrollTop / rowHeight.value
	const newYear = Math.round(startYear.value + rowsDown)
	const newDate = Date.UTC(newYear, 0, getDayOfYear(model.value))
	setDate(newDate)
	// console.log('scrolled to year', newYear)
}
watch(isOverview, (newVal) => {
	// console.log('isOverview changed to', newVal)
	if (newVal) {
		autoScrolling.value = true
	} else {
		// @ts-ignore
		scroller.value!.style.overflow = 'hidden'
		setTimeout(
			() => {
				// console.log('isOverview: re-enabling scrolling')
				autoScrolling.value = false
				if (scroller.value === null) return
				// @ts-ignore
				scroller.value!.style.overflow = 'auto'
				scroller.value!.scrollTop =
					(selectedYear.value - startYear.value) * rowHeight.value
			},
			intervalToMs(scssVars.animTime) + 50,
		)
	}
	// if(newVal) {
	// 	autoScrolling.value = true
	// } else {
	// 	autoScrolling.value = false
	// }
})

const timeReelWorker = new TimeReelWorker()
timeReelWorker.onmessage = (e: MessageEvent) => {
	const {
		newDs,
		eventBoxesForYear: newEventBoxes,
		maxSimultaneousEvents: newMax,
	} = e.data as {
		newDs: Record<number, string>
		eventBoxesForYear: Record<number, EventBox[]>
		maxSimultaneousEvents: number
	}

	// console.log('TimeReel: received worker data, maxSimultaneousEvents=', newMax)
	eventBoxesForYear.value = newEventBoxes
	maxSimultaneousEvents.value = newMax
	const yearsList = [...years.value].reverse()
	const drawNextYear = () => {
		if (!yearsList.length) {
			return
		}

		const year = yearsList.shift()!
		let currentPath = null
		try {
			currentPath = d3.select(`#events-line-${year}`).attr('d')
		} catch (e) {
			// Sometimes happens on first draw in race conditions
		}
		if (currentPath !== newDs[year]) {
			// The line has changed, redraw it
			d3.select(`#events-line-${year}`)
				.transition()
				.duration(intervalToMs(scssVars.animTime))
				.attr('d', newDs[year])
		}

		// We can use this if it's blocking the UI, but the result will be a staggered draw,
		// so should be avoided if possible. Same is true of setTimeout.
		// requestAnimationFrame(drawNextYear)
		drawNextYear()
	}
	requestAnimationFrame(drawNextYear)
}
watch(
	() => props.events,
	(newVal) => {
		timeReelWorker.postMessage({
			events: props.events.map((e) => ({
				id: e.id,
				times: [...e.times],
				event_type: e.event_type,
				color: props.colorForEvent(e),
			})),
			years: years.value,
			mixedEvents: props.eventType === 'hotcold',
			start: props.start.getTime(),
			end: props.end.getTime(),
		})
	},
	{ immediate: true, deep: false },
)

watch(
	() => [props.selectedEvent, isOverview],
	(newVal, oldVal) => {
		// When the selected event changes, ensure the year is in view
		// In timeline mode, this happens instantly, at the same time as the line transition,
		// so that we don't see any movement, but we are in the right place to transition back to default mode,
		// console.log(
		// 	'selected event changed, scrolling to',
		// 	selectedYear.value,
		// 	rowsToShow.value,
		// )
		if ((newVal[0] !== oldVal[0] || newVal[1]) && scroller.value) {
			// console.log(
			// 	'TimeReel: selected event changed, scrolling to',
			// 	selectedYear.value,
			// )
			const yearsOffset = selectedYear.value - startYear.value
			const scrollOffset = 0.5 * (yearsOffset * 2)
			scroller.value.scrollTo({
				top: scrollOffset * rowHeight.value,
				behavior: 'auto',
			})
		}
	},
)

watch(
	() => [props.start, props.end],
	() => {
		if (model.value > props.end) {
			model.value = new Date(props.end.getTime())
		} else if (model.value < props.start) {
			model.value = new Date(props.start.getTime())
		}
	},
)

const xScaleFactor = computed(() => {
	const panelWidth = document.getElementById(
		'event-graph-width-el',
	)?.clientWidth
	const totalWidth = timeReelRef.value?.clientWidth

	return panelWidth && totalWidth ? totalWidth / panelWidth : 1.0
})
const xOffset = computed(() => {
	const paddingOffset = document
		.getElementById('event-graph-width-el')
		?.getBoundingClientRect().left
	const panelOffset = document
		.getElementById('event-graphs')
		?.getBoundingClientRect().left

	return paddingOffset! - panelOffset! || 0
})
const viewportTransform = computed(() => {
	if (props.selectedEvent && isZoom.value) {
		const eventStart = getDayOfYear(props.selectedEvent.times[0])
		const eventEnd = getDayOfYear(
			props.selectedEvent.times[props.selectedEvent.times.length - 1],
		)
		const nDays = (eventEnd - eventStart + 2) * xScaleFactor.value
		const scale = Math.max(1, 366 / nDays)
		const pxPerDay = (timeReelRef.value?.clientWidth || 1) / nDays

		// return 'translate(0, 0)'
		// console.log( `scale(${scale}, 1) translate(${-(eventStart - 1)}, 0) translate(${xOffset.value / pxPerDay}, 0)`)
		return `scale(${scale}, 1) translate(${-(eventStart - 1)}, 0) translate(${xOffset.value / pxPerDay}, 0)`
	} else {
		// console.log('translate(0, 0)')
		return 'translate(0, 0)'
	}
})

const lineTransform = computed(() => {
	return (year: number): string =>
		isTimeline.value
			? `translate(0,${selectedYear.value - year}) scale(${1.0 / years.value.length}, 1)`
			: isOverview.value
				? `translate(${1 - differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)},0) scale(1,1.5)`
				: `translate(${1 - differenceInDays(new Date(Date.UTC(year, 0, 1)), props.start)},0)`
})

const yearTransform = computed(() => {
	return (year: number): string =>
		`translate(0, ${year - startYear.value + 0.5})`
})

const lineOpacity = computed(() => {
	return (year: number): number => {
		return props.showBars && selectedYear.value === year && !isTimeline.value
			? 0.1
			: 1
	}
})

const yearPadding = computed(() => {
	if (isOverview.value) return 0
	return (rowsToShow.value - 1) * 0.5 * rowHeight.value
})

const dayBoxes = (boxes: EventBox[]): EventBox[] => {
	const ret = []
	for (let box of boxes) {
		for (let day = box.startX; day <= box.endX; day++) {
			ret.push({
				...box,
				startX: day,
				endX: day,
			})
		}
	}
	return ret
}

const scrubberTranslate = computed(() => {
	const xOffsetPx =
		localScrubberOffset.value !== null
			? localScrubberOffset.value[0] + initialScrubberPos.value[0]
			: needleOffsetPx.value - 12
	const yOffsetPx =
		localScrubberOffset.value !== null
			? localScrubberOffset.value[1] + initialScrubberPos.value[1]
			: (selectedYear.value - startYear.value + 0.5) * rowHeight.value - 24
	// console.log(
	// 	'scrubberTranslate:',
	// 	xOffsetPx,
	// 	yOffsetPx,
	// 	rowHeight.value,
	// 	selectedYear.value,
	// 	startYear.value,
	// )
	return `translate(${xOffsetPx}px, ${yOffsetPx}px)`
})

const dateTranslate = computed(() => {
	if (isOverview.value) {
		const xOffsetPx = needleOffsetPx.value
		const yOffsetPx =
			localScrubberOffset.value !== null
				? localScrubberOffset.value[1] + initialScrubberPos.value[1]
				: (selectedYear.value - startYear.value + 0.5) * rowHeight.value - 24
		return `translate(calc(-50% + ${xOffsetPx}px), ${yOffsetPx}px)`
	} else {
		return `translateY(${hasMoved.value ? 300 : 0}%) translateX(${hasMoved.value ? needleOffsetPx.value + 2 : scroller.value?.clientWidth! / 2}px) translateX(-50%)`
	}
})
</script>

<template>
	<div class="time-reel" ref="timeReelRef">
		<div
			class="date-info mono"
			:class="{ dragging: hasMoved }"
			:style="`transform: ${dateTranslate}`"
		>
			{{ dayStr(selectedDay, selectedYear, isOverview) }}
		</div>
		<div
			class="controls"
			:class="{
				hidden: isOverview,
				zoom: isZoom,
				timeline: isTimeline,
			}"
		>
			<div class="buttons">
				<button
					class="glassy color"
					@click="startOfYear"
					v-tooltip="
						isTimeline
							? $l.startOfTimeline
							: selectedEvent
								? $l.startOfEvent
								: $l.startOfYear
					"
				>
					<IconChevronLeftPipe aria-hidden="true" />
				</button>
				<button
					class="glassy color"
					@click.stop="prevDay"
					:disabled="selectedYear <= startYear && selectedDay <= 1"
					v-tooltip="isTimeline ? $l.prevTimestep : $l.prevDay"
				>
					<IconChevronLeft aria-hidden="true" />
				</button>
				<button
					class="glassy color"
					@click="togglePlay"
					v-tooltip="playing ? $l.pause : $l.play"
					:disabled="
						isZoom &&
						(!props.selectedEvent ||
							props.selectedEvent.times[0] > model.getTime() ||
							props.selectedEvent.times[props.selectedEvent.times.length - 1] <
								model.getTime())
					"
					:class="{ selected: playing }"
				>
					<IconPlayerPlay aria-hidden="true" v-if="!playing" />
					<IconPlayerPause aria-hidden="true" v-else />
				</button>
				<button
					class="glassy color"
					@click="nextDay"
					:disabled="selectedYear >= endYear && selectedDay >= 365"
					v-tooltip="isTimeline ? $l.nextTimestep : $l.nextDay"
				>
					<IconChevronRight aria-hidden="true" />
				</button>
				<button
					class="glassy color"
					@click="endOfYear"
					v-tooltip="
						isTimeline
							? $l.endOfTimeline
							: selectedEvent
								? $l.endOfEvent
								: $l.endOfYear
					"
				>
					<IconChevronRightPipe aria-hidden="true" />
				</button>
			</div>
		</div>
		<div
			class="scroller"
			ref="scrollerRef"
			@scroll="scrollListener"
			@mousedown.self="startDrag"
			:class="{
				timeline: isTimeline,
				overview: isOverview,
				eventzoom: isZoom,
				dragging: hasMoved,
			}"
		>
			<div
				class="scrubber"
				v-if="isOverview"
				:style="`transform: ${scrubberTranslate}; pointer-events: auto;`"
				@mousedown="startDrag"
			>
				<IconCrosshair />
			</div>
			<div class="scrollee" :style="`margin: ${yearPadding}px 0;`">
				<div
					v-for="year in years"
					:key="year"
					:style="`height: ${rowHeight}px;`"
					class="year"
					:class="{
						timeline: mode === 'timeline',
						highlight: year === selectedYear,
						odd: year % 2 === 1,
						'last-year': year === endYear,
					}"
				>
					<h1 class="label" :style="`opacity: ${isTimeline ? 0 : 1}`">
						{{ year }}
					</h1>
				</div>
				<div class="clipper">
					<svg
						class="events-svg"
						ref="containerRef"
						xmlns="http://www.w3.org/2000/svg"
						:viewBox="`0 0 366 ${endYear - startYear + 1}`"
						preserveAspectRatio="none"
					>
						<defs>
							<linearGradient id="heatColdGradient" x1="0" y1="0" x2="0" y2="1">
								<stop offset="0%" :stop-color="scssVars.c3sred" />
								<stop offset="49%" :stop-color="scssVars.c3sred" />
								<stop offset="51%" :stop-color="scssVars.c3sblue" />
								<stop offset="100%" :stop-color="scssVars.c3sblue" />
							</linearGradient>
							<filter
								id="blur"
								x="-20%"
								y="-20%"
								width="140%"
								height="140%"
								primitiveUnits="objectBoundingBox"
							>
								<feGaussianBlur stdDeviation="0.00051 0.0051" />
								<feComponentTransfer>
									<feFuncA type="linear" slope="0.6" />
								</feComponentTransfer>
								<!-- Drop saturation by 50% -->
								<feColorMatrix type="saturate" values="0.5" />
							</filter>

							<filter
								id="dropShadow"
								x="-50%"
								y="-50%"
								width="200%"
								height="200%"
								primitiveUnits="objectBoundingBox"
							>
								<feDropShadow
									dx="0.02"
									dy="0.3"
									stdDeviation="0.02 0.1"
									flood-color="var(--highlight)"
								/>
							</filter>

							<filter
								id="halo"
								x="-50%"
								y="-50%"
								width="200%"
								height="200%"
								primitiveUnits="objectBoundingBox"
							>
								<!-- Slight halo -->
								<feGaussianBlur
									in="SourceAlpha"
									stdDeviation="0.03"
									result="blurred"
								/>
								<feFlood flood-color="var(--highlight)" result="color" />
								<feComposite
									in="color"
									in2="blurred"
									operator="in"
									result="halo"
								/>

								<!-- Boost saturation -->
								<feColorMatrix
									in="halo"
									type="saturate"
									values="1.5"
									result="haloSaturated"
								/>

								<!-- Merge original graphic on top -->
								<feMerge>
									<feMergeNode in="haloSaturated" />
									<feMergeNode in="SourceGraphic" />
								</feMerge>
							</filter>
						</defs>

						<g :transform="viewportTransform">
							<g
								v-for="year in years"
								:key="year"
								class="year-group"
								:transform="yearTransform(year)"
							>
								<rect
									v-for="(month, i) in monthsForYear(
										year,
										isDefault || isOverview,
										$l,
									)"
									:key="`year-bg-${year}-month-${i}`"
									class="background month-bg"
									:class="{ odd: i % 2 === 0 }"
									:x="month.startX"
									:width="month.length"
									:y="-0.5"
									:height="1"
									:opacity="isZoom || isTimeline ? 0 : 1"
								/>
								<rect
									v-for="year in years"
									:key="`year-bg-${year}`"
									class="background month-bg"
									:class="{ odd: year % 2 === 0 }"
									:x="(year - startYear) * (366 / years.length)"
									:width="366 / years.length"
									:y="-0.5"
									:height="1"
									:opacity="isTimeline ? 1 : 0"
								/>
							</g>
							<g
								v-for="year in years"
								:key="year"
								class="year-group"
								:transform="yearTransform(year)"
							>
								<path
									:id="`events-line-${year}`"
									class="event-line"
									:class="{
										hot:
											props.eventType === 'hot' ||
											props.eventType === 'hotcold',
										cold:
											props.eventType === 'cold' ||
											props.eventType === 'hotcold',
									}"
									d=""
									vector-effect="non-scaling-stroke"
									:stroke-width="3"
									:transform="lineTransform(year)"
									:opacity="lineOpacity(year)"
									:filter="isZoom ? 'url(#blur)' : ''"
								/>
								<g
									tag="g"
									name="daily-event-fx"
									v-if="(showBars && props.mode !== 'overview') || isZoom"
									:filter="isZoom ? 'url(#blur)' : ''"
								>
									<rect
										v-if="year === selectedYear"
										v-for="box in eventBoxesForYear[year]"
										class="event-bar"
										:data-id="`${box.startX}-${box.endX}`"
										:class="{
											[box.type]: true,
										}"
										:fill="box.color || scssVars.c3sred"
										:x="box.startX - year * TOTAL_DAYS"
										:width="box.endX - box.startX + 1"
										:y="positionY(box.y, box.type)"
										:height="eventHeight"
										:key="box.eventId"
										vector-effect="non-scaling-stroke"
										@click="eventClicked(box)"
										@mouseover="eventHovered(box)"
									></rect>
									<rect
										v-if="hoverEvent !== null && year === selectedYear"
										v-for="box in eventBoxesForYear[year].filter(
											(box) => box.eventId === hoverEvent!.id,
										)"
										class="event-bar"
										:data-id="`${box.startX}-${box.endX}-highlight`"
										:class="{
											[box.type]: true,
										}"
										:fill="scssVars.lightbulb"
										:x="box.startX - year * TOTAL_DAYS"
										:width="box.endX - box.startX + 1"
										:y="positionY(box.y, box.type)"
										:height="eventHeight"
										:key="box.eventId + '-highlight'"
										stroke-width="2"
										vector-effect="non-scaling-stroke"
										filter="url(#halo)"
										@click="isZoom ? () => {} : eventClicked(box)"
										@mouseleave="eventHovered(null)"
									></rect>
								</g>
								<!-- Draw selected event on top. This ensures it is always visible even if overlapping other events -->
								<g filter="url(#halo)">
									<rect
										v-if="
											isZoom &&
											props.selectedEvent !== null &&
											year === selectedYear
										"
										v-for="(box, i) in dayBoxes(
											eventBoxesForYear[year].filter(
												(b) => b.eventId === props.selectedEvent?.id,
											),
										)"
										class="event-bar selected"
										:data-id="`${box.startX}-${box.endX}`"
										:class="{
											[box.type]: true,
										}"
										:fill="box.color || scssVars.c3sred"
										:x="-0.5 + box.startX - year * TOTAL_DAYS"
										:width="box.endX - box.startX + 0.9"
										:y="positionY(box.y, box.type)"
										:height="
											isZoom
												? props.eventType === 'hotcold'
													? 0.75 * eventHeight
													: 1.5 * eventHeight
												: props.eventType === 'hotcold'
													? 0.5 * eventHeight
													: eventHeight
										"
										:key="`${box.eventId}-${i}`"
										vector-effect="non-scaling-stroke"
										@click="model = new Date(props.selectedEvent.times[i])"
									></rect>
								</g>
							</g>
						</g>
					</svg>
				</div>
			</div>
		</div>

		<div
			class="year-highlights"
			@prevent.default
			:class="{
				timeline: isTimeline,
				overview: isOverview,
				eventzoom: isZoom,
				showbars: showBars,
			}"
		>
			<div
				class="highlight-row fade-top"
				:class="{ examining: isDefault }"
				:style="`height: ${topRowHeight};`"
			></div>
			<div
				class="highlight-row highlight"
				:style="`height: ${highlightRowHeight};`"
				:class="{ examining: isDefault }"
			>
				<div
					class="needle"
					:class="{
						indicator: selectedEvent && isTimeline,
					}"
					ref="needleRef"
					v-if="isDefault || isZoom || selectedEvent"
					:style="`transform: translateX(calc(${needleOffsetPx - 6}px));`"
					@mousedown="startDrag"
				>
					<div class="line" />
				</div>
				<div
					class="needle range off"
					v-if="isTimeline"
					:style="`transform: translateX(0px); width: ${Math.round(startNeedleOffsetPx - 2)}px;`"
				></div>
				<div
					class="needle range off"
					v-if="isTimeline"
					:style="`transform: translateX(calc(${endNeedleOffsetPx - 4}px)); width: calc(100% - ${Math.round(endNeedleOffsetPx - 6)}px);`"
				></div>
				<div
					class="needle range"
					v-if="isTimeline"
					:style="`transform: translateX(calc(${startNeedleOffsetPx - 3}px)); width: calc(${endNeedleOffsetPx - startNeedleOffsetPx + 3}px);`"
					@mousedown="startDrag"
				>
					<div class="start-handle handle" v-tooltip="$l.startHandle">
						<IconArrowBarToLeft />
					</div>
					<div class="grab-area handle" v-tooltip="$l.grabHandle">
						<IconArrowsMove />
					</div>
					<div class="end-handle handle" v-tooltip="$l.endHandle">
						<IconArrowBarToRight />
					</div>
				</div>
				<div class="month-labels" v-if="!isZoom && !isTimeline">
					<p v-show="!isZoom" class="jan">{{ $l.months.jan }}</p>
					<p v-show="!isZoom" class="feb">{{ $l.months.feb }}</p>
					<p v-show="!isZoom" class="mar">{{ $l.months.mar }}</p>
					<p v-show="!isZoom" class="apr">{{ $l.months.apr }}</p>
					<p v-show="!isZoom" class="may">{{ $l.months.may }}</p>
					<p v-show="!isZoom" class="jun">{{ $l.months.jun }}</p>
					<p v-show="!isZoom" class="jul">{{ $l.months.jul }}</p>
					<p v-show="!isZoom" class="aug">{{ $l.months.aug }}</p>
					<p v-show="!isZoom" class="sep">{{ $l.months.sep }}</p>
					<p v-show="!isZoom" class="oct">{{ $l.months.oct }}</p>
					<p v-show="!isZoom" class="nov">{{ $l.months.nov }}</p>
					<p v-show="!isZoom" class="dec">{{ $l.months.dec }}</p>
				</div>
			</div>
			<div
				class="highlight-row fade-bottom"
				:class="{ examining: isDefault }"
				:style="`height: ${bottomRowHeight};`"
			></div>
		</div>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;
@use 'sass:color';

// $fitTime: $animTime * 0.25;
// $zoomTime: 3 * $animTime * 0.25;

.time-reel {
	position: relative;
	// overflow-y: scroll;
	height: 100%;
	overflow: visible;

	.date-info {
		position: absolute;
		left: 0;
		bottom: 100%;
		z-index: 30;
		background: linear-gradient(
			var(--panel-solid),
			var(--panel-solid) 50%,
			var(--panel-bg-alt) 100%
		);
		backdrop-filter: $frosty;
		padding: 0.25rem 0.5rem;
		font-size: 0.875rem;
		user-select: none;
		border-radius: $borderRadius;
		border-bottom-right-radius: 0;
		border-bottom-left-radius: 0;
		transition: transform 0.1s linear;

		&.dragging {
			transition: transform 0s linear;
			border-radius: $borderRadius;
		}
	}
	&.overview {
		.date-info {
			z-index: 1000;
		}
	}
	&.timeline {
		.date-info {
			display: none;
		}
	}

	.controls {
		// height: 2rem;
		position: absolute;
		top: 0.25rem;
		left: 50%;
		transform: translate(-50%, 0%);
		z-index: 3;
		padding: 0;
		font-size: 0.875rem;
		user-select: none;
		display: flex;
		transition: all $transition;
		&.zoom {
			left: 17%;
			top: calc(100% - 1.75rem);
			// top: auto;
		}

		.buttons {
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: center;
			gap: 0;
			button {
				width: 2.75rem;
				border-radius: 0;
				margin: 0;
				height: 1.75rem;
				display: flex;
				align-items: center;
				font-size: 0.85rem;
				padding: 0.5rem 0.8rem;
				justify-content: center;

				&:first-child {
					border-top-left-radius: 0.25rem;
					border-bottom-left-radius: 0.25rem;
				}
				&:last-child {
					border-top-right-radius: 0.25rem;
					border-bottom-right-radius: 0.25rem;
				}
			}
		}

		&.timeline {
			top: calc(100% - 1.75rem);
			left: 50%;
			transform: translate(-50%, 0%);
		}

		&.hidden {
			display: none;
		}
	}

	.scroller {
		width: 100%;
		height: 100%;
		overflow-y: auto;
		position: relative;
		scroll-snap-type: y mandatory;
		display: block;
		z-index: 1;
		&.dragging {
			cursor: ew-resize;
		}
		contain: layout;

		.scrubber {
			position: absolute;
			top: 12px;
			width: 3rem;
			color: var(--highlight);
			opacity: 1;
			z-index: 5;
			pointer-events: none;
			cursor: grab;

			.tabler-icon {
				filter: drop-shadow(1px 1px 2px rgba(0, 0, 0, 1))
					drop-shadow(1px 1px 5px rgba(0, 0, 0, 1))
					drop-shadow(1px 1px 8px rgba(0, 0, 0, 1));

				height: auto;
			}
		}

		&.dragging {
			.scrubber {
				cursor: grabbing;
			}
		}

		&.eventzoom,
		&.timeline {
			overflow-y: hidden;
		}

		.scrollee {
			position: relative;
			width: 100%;
			background-color: transparent;
			pointer-events: none;

			.clipper {
				position: absolute;
				top: 0;
				bottom: 0;
				width: 100%;
				height: 100%;
				overflow: hidden;
				// pointer-events: none;

				.events-svg {
					position: absolute;
					transition: all $transition;
					top: 0;
					left: 0;
					height: 100%;
					background-color: transparent;
					width: 100%;
					margin: 0;
					padding: 0;
					overflow: visible;
					.background {
						transition: all $transition;
					}
				}
			}

			.year {
				transition:
					all $transition,
					height 0s linear;

				scroll-snap-align: center;
				display: flex;
				flex-direction: row;
				align-items: flex-end;
				justify-content: flex-start;
				width: 100%;
				position: relative;
				pointer-events: none;

				&.timeline {
					font-size: 1.5rem;
					color: var(--text-secondary);
					margin: 0;
					padding: 0.5rem 0.5rem;
					transition: opacity 0s linear;
					user-select: none;
				}
			}
		}
		background: var(--panel-bg);
		backdrop-filter: $frosty;
		&.overview {
			overflow-y: visible;
			transition:
				opacity $transition,
				backdrop-filter $transition,
				background $transition;
			&.dragging {
				background: transparent;
				backdrop-filter: blur(1px);
				opacity: 0.6;
				cursor: move;
			}
			.event-line {
				stroke-width: 2;
				opacity: 1;
				fill-opacity: 0.8;
			}
			.scrollee {
				overflow-y: visible;
				.year {
					align-items: center;
					user-select: none;
					.label {
						font-size: 0.75rem !important;
						padding: 0.125rem 0.25rem;
						background: var(--panel-solid);
					}
				}
				.clipper {
					.events-svg {
						margin-left: 2.5rem;
						// margin-bottom: 1.5rem;
						width: calc(100% - 2.5rem);
						height: calc(100%);
					}
				}
			}
		}
	}

	.event-line {
		stroke: $c3sblue;
		stroke-width: 3;
		fill: $c3sblue;
		fill-opacity: 0.25;
		pointer-events: none;
		transition: opacity 0.5 * $animTime linear;

		&.hot {
			stroke: $c3sred;
			fill: $c3sred;
		}
		&.cold {
			stroke: $c3sblue;
			fill: $c3sblue;
		}
		&.hot.cold {
			stroke: url(#heatColdGradient);
			fill: url(#heatColdGradient);
		}
	}

	.timeline {
		.event-line {
			stroke-width: 0.5;
			transition: all 0 linear;
		}
		.highlight-row {
			transition: all $transition;
		}
	}

	.year-highlights {
		pointer-events: none;
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		display: block;
		z-index: 2;
		transition: all $transition;
		border: none;
		overflow: hidden;

		$fadeColor: #aaaaaa;

		&.overview {
			.month-labels {
				display: none !important;
			}
		}

		.highlight-row {
			transition: all $transition;
			overflow: hidden;
			pointer-events: none;

			&.fade-top {
				border-top-left-radius: $borderRadius;
				border-top-right-radius: $borderRadius;
				pointer-events: none;
				background: linear-gradient(
					to top,
					rgba($fadeColor, 0.3),
					rgba($fadeColor, 0.8)
				);
				&.exploring {
					background: linear-gradient(
						to top,
						rgba($fadeColor, 0.1),
						rgba($fadeColor, 0.5)
					);
				}
			}
			&.fade-bottom {
				border-bottom-left-radius: $borderRadius;
				border-bottom-right-radius: $borderRadius;
				pointer-events: none;
				background: linear-gradient(
					to bottom,
					rgba($fadeColor, 0.3),
					rgba($fadeColor, 0.8)
				);
				&.exploring {
					background: linear-gradient(
						to top,
						rgba($fadeColor, 0.5),
						rgba($fadeColor, 0.1)
					);
				}
			}
			&.highlight {
				position: relative;
				width: 100%;
				display: flex;
				flex-direction: row;
				align-items: stretch;
				color: #aaaaaa;
				box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
				&.exploring {
					box-shadow: 0 0 5px rgba($fadeColor, 0.5);
				}
				pointer-events: none;

				.needle {
					pointer-events: auto;
					display: block;
					position: absolute;
					top: 0;
					left: 0;
					margin-left: -2px;
					background-color: transparent;
					transform-origin: left center;
					width: 3px;
					height: 100%;
					box-sizing: border-box;
					cursor: ew-resize;
					border-top: 0.5rem solid var(--primary-active);
					border-right: 0.5rem solid rgba($lightbulb, 0.25);
					border-left: 0.5rem solid rgba($lightbulb, 0.25);
					border-bottom: none;
					transform: translateX(-50%);

					&.range {
						background: transparent;

						&.off {
							background: rgba(black, 0.1);
							border-top: none;
							border-right: none;
							border-left: none;
							backdrop-filter: blur(1px);
						}
						opacity: 1;
						height: 100%;

						border-top: 0.5rem solid var(--primary-active);
						border-right: 0.25rem solid rgba($lightbulb, 0.5);
						border-left: 0.25rem solid rgba($lightbulb, 0.5);

						display: flex;
						flex-direction: row;
						pointer-events: none;
						cursor: default;
						// align-items: stretch;
						// justify-content: stretch;

						.handle {
							pointer-events: auto;
							display: flex;
							justify-content: center;
							align-items: center;
							&.start-handle {
								cursor: w-resize;
								flex: 1 1 25%;
								// background-color: blue;
							}
							&.end-handle {
								cursor: e-resize;
								flex: 1 1 25%;
								// background-color: green;
							}
							&.grab-area {
								cursor: grab;
								flex: 1 1 50%;
								// background-color: red;
							}

							.tabler-icon {
								color: var(--highlight);
								// color: black;
								flex: 1 1 50%;
								height: 50%;
								opacity: 0.05;
								transition: opacity $transition;
								pointer-events: none;
							}

							&:hover .tabler-icon {
								opacity: 0.75;
								filter: drop-shadow(1px 1px 2px rgba(0, 0, 0, 1));
							}
						}
					}

					.line {
						position: absolute;
						left: -1px;
						width: 2px;
						height: 100%;
						background-color: var(--primary-active);
						cursor: ew-resize;
					}

					&.indicator {
						transition: all $transition;
					}
				}
				.month-labels {
					flex: 0 0 100%;
					pointer-events: none;
					user-select: none;
					display: flex;
					flex-direction: row;
					color: var(--text-secondary);
					p {
						pointer-events: none;
						user-select: none;
						flex-grow: 1;
						text-align: center;
						margin: 0;
						display: flex;
						justify-content: center;
						align-items: flex-end;
					}

					.jan {
						flex-basis: 31fr;
					}
					.feb {
						flex-basis: 28fr;
					}
					.mar {
						flex-basis: 31fr;
					}
					.apr {
						flex-basis: 30fr;
					}
					.may {
						flex-basis: 31fr;
					}
					.jun {
						flex-basis: 30fr;
					}
					.jul {
						flex-basis: 31fr;
					}
					.aug {
						flex-basis: 31fr;
					}
					.sep {
						flex-basis: 30fr;
					}
					.oct {
						flex-basis: 31fr;
					}
					.nov {
						flex-basis: 30fr;
					}
					.dec {
						flex-basis: 31fr;
					}
				}
			}
		}
	}

	.events-svg {
		background-color: transparent;
		pointer-events: none;

		.year-group {
			transition: all $transition;
			background-color: transparent;

			.background.month-bg {
				fill: var(--panel-hint2);

				&.odd {
					fill: var(--panel-hint);
				}
			}
		}

		.background {
			pointer-events: none;
			stroke: 0;
		}

		.event-bar {
			cursor: pointer;
			pointer-events: auto;
			transition: all $transition;
			stroke-width: 0.5;
			opacity: 1 !important;

			&.hot {
				stroke: $c3sred;
			}
			&.cold {
				stroke: $c3sblue;
			}
			&.selected {
				stroke: black;
				stroke-width: 0.5;
				pointer-events: auto;
				cursor: pointer;
				// fill: black;
				// transform: scaleY(-3);
			}
		}

		.event-blur {
			pointer-events: none;
			backdrop-filter: $frosty;
		}

		.day-box {
			stroke-width: 2;
			opacity: 1;
		}

		.daily-event-fx-enter-from {
			opacity: 0;
			transition: opacity $transition;
		}
		.daily-event-fx-enter-to {
			opacity: 1;
		}

		.daily-event-fx-leave-from {
			opacity: 1;
			transition: opacity $transition;
		}
		.daily-event-fx-leave-to {
			opacity: 0;
		}
	}
}
</style>
