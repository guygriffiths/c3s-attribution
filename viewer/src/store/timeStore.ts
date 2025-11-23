import { defineStore } from 'pinia'

interface TimeState {
	selectedTime: Date

	startTime: Date
	endTime: Date

	startTimeFilter: Date | null
	endTimeFilter: Date | null

	showBars: boolean

	timePanelExpanded: boolean

	isPlaying: boolean
}

export const useStore = defineStore('time', {
	state: (): TimeState => {
		return {
			// The currently selected time
			selectedTime: new Date(Date.UTC(2024, 4, 28, 0, 0, 0)),

			// Range for the whole thing
			startTime: new Date(1979, 0, 1),
			endTime: new Date(),

			// Selected range for filtering in heatmap mode
			startTimeFilter: null,
			endTimeFilter: null,

			// Whether to plot individual events as bars in the time reel
			showBars: false,

			// Whether the time panel is expanded - i.e. in overview mode
			timePanelExpanded: false,

			// Whether animation is currently playing
			isPlaying: false,
		}
	},
	getters: {
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
	},
	actions: {},
})

export type TimeStore = ReturnType<typeof useStore>
