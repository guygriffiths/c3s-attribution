import { defineStore } from 'pinia'

interface TimeState {
	// The time selected in the time reel. This will always correspond to the time plotted in the event explorer view
	selectedTime: Date
	

	startTime: Date
	endTime: Date

	showBars: boolean // Whether to show the bars in the time reel

	timePanelVisible: boolean
	timePanelExpanded: boolean
}

export const useStore = defineStore('time', {
	state: (): TimeState => {
		return {
			selectedTime: new Date(Date.UTC(1998, 4, 28, 0, 0, 0)),
			startTime: new Date(1979, 0, 1),
			endTime: new Date(),
			showBars: false,

			timePanelExpanded: false,
			timePanelVisible: true,
		}
	},
	getters: {
		isoDatetime: (state) => {
			// This always returns the datetime in UTC, which is what we need
			return state.selectedTime.toISOString()
		},
	},
	actions: {
		toggleTimePanel() {
			this.timePanelExpanded = !this.timePanelExpanded
		},
	}
})

export type TimeStore = ReturnType<typeof useStore>
