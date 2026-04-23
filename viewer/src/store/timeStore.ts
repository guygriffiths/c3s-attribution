import { addDays } from 'date-fns'
import { defineStore } from 'pinia'

interface TimeState {
	selectedTime: Date

	startTime: Date
	endTime: Date

	startTimeFilter: Date
	endTimeFilter: Date

	showBars: boolean

	timePanelExpanded: boolean

	isPlaying: boolean

	speedFactor: number
}

export const useStore = defineStore('time', {
	state: (): TimeState => {
		return {
			// The currently selected time
			selectedTime: new Date(Date.UTC(1981, 4, 28, 0, 0, 0)),

			// Range for the whole thing
			startTime: new Date(1979, 0, 1),
			endTime: new Date(),

			// Selected range for filtering in heatmap mode
			startTimeFilter: new Date(1979, 0, 1),
			endTimeFilter: new Date(),

			// Whether to plot individual events as bars in the time reel
			showBars: true,

			// Whether the time panel is expanded - i.e. in overview mode
			timePanelExpanded: false,

			// Whether animation is currently playing
			isPlaying: false,

			// Speed factor for time reel animation
			speedFactor: 1
		}
	},
	getters: {
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
	},
	actions: {
		nextDay() {
			if(this.selectedTime < this.endTime) {
				this.selectedTime = addDays(this.selectedTime, 1)
			}
		},
		prevDay() {
			if(this.selectedTime > this.startTime) {
				this.selectedTime = addDays(this.selectedTime, -1)
			}
		}
	},
})

export type TimeStore = ReturnType<typeof useStore>
