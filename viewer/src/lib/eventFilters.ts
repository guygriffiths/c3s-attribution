import {
	getCurrentEvents,
	getParameterFilteredEvents,
	getSpaceTimeFilteredEvents,
	getSpatiallyFilteredEvents,
	onParameterFilterChanged,
	onSpaceTimeFilterChanged,
	onSpatialFilterChanged,
	setEventTypeFilter,
	setTimeRangeFilter,
} from '@/lib/eventsDB'
import { useStore as useEventStore } from '@/store/eventStore'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { ref, watch } from 'vue'


export const useEventFilters = () => {
	const store = useStore()
	const eventStore = useEventStore()
	const timeStore = useTimeStore()
	// Time reel events - filtered spatially and manually, but not temporally
	const timeReelEvents = ref<ExtremeEvent[]>([])

	onSpatialFilterChanged(() => {
		timeReelEvents.value = getSpatiallyFilteredEvents()
	})

	watch(
		() => [store.exploreGlobal],
		() => {
			if (store.exploreGlobal) {
				timeReelEvents.value = getParameterFilteredEvents()
			} else {
				timeReelEvents.value = getSpatiallyFilteredEvents()
			}
		},
		{ immediate: true },
	)

	// Summary events - filtered spatially, manually, and temporally
	const summaryEvents = ref<ExtremeEvent[]>([])

	const updateSummaryEvents = () => {
		if (store.viewMode === 'timemachine') {
			summaryEvents.value = getCurrentEvents(timeStore.selectedTime, true)
		} else {
			summaryEvents.value = getSpaceTimeFilteredEvents()

			// Ensure selected event is included
			if (eventStore.selectedEvent) {
				if (
					!summaryEvents.value.find(
						(e) => e.id === eventStore.selectedEvent?.id,
					)
				) {
					// @ts-ignore
					summaryEvents.value.push(eventStore.selectedEvent)
				}
			}
		}
	}

	onSpaceTimeFilterChanged(updateSummaryEvents)

	watch(() => [store.viewMode, timeStore.selectedTime], updateSummaryEvents, {
		immediate: true,
	})

	// Background events for multi-event panel when filtering spatially
	const globalFilteredEvents = ref<ExtremeEvent[]>([])

	onParameterFilterChanged(() => {
		globalFilteredEvents.value = getParameterFilteredEvents()
		if (store.exploreGlobal) {
			timeReelEvents.value = globalFilteredEvents.value
		}
	})

	// Sync time range filter with store
	watch(
		() => [timeStore.startTimeFilter, timeStore.endTimeFilter],
		() => {
			setTimeRangeFilter(timeStore.startTimeFilter, timeStore.endTimeFilter)
		},
		{ immediate: true },
	)

	// Sync event type filter with store
	watch(
		() => [eventStore.eventTypeMode],
		() => {
			if (eventStore.eventTypeMode === 'cold') {
				setEventTypeFilter(false, true)
			} else if (eventStore.eventTypeMode === 'hot') {
				setEventTypeFilter(true, false)
			} else {
				setEventTypeFilter(true, true)
			}
		},
		{ immediate: true },
	)
	return { timeReelEvents, summaryEvents, globalFilteredEvents }
}
