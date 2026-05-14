// lib/help.ts
import { IconInfoCircle, IconRainbow, IconTrophy } from '@tabler/icons-vue'
import { Component, defineAsyncComponent, shallowRef } from 'vue'

export type HelpTextEntry = {
	title: string
	component: Component // Instead of html string
	target?: string
	on?: 'top' | 'bottom' | 'left' | 'right'
	icon?: Component
}

const eventInfoHelp = defineAsyncComponent(
	() => import('@/components/help/EventInfoHelp.vue'),
)
const timeReelHelp = defineAsyncComponent(
	() => import('@/components/help/TimeReelHelp.vue'),
)
const hamburgerMenuHelp = defineAsyncComponent(
	() => import('@/components/help/HamburgerMenuHelp.vue'),
)
const eventDayPanelHelp = defineAsyncComponent(
	() => import('@/components/help/EventDayPanelHelp.vue'),
)
const eventGraphsHelp = defineAsyncComponent(
	() => import('@/components/help/EventGraphsHelp.vue'),
)
const multiEventPanelHelp = defineAsyncComponent(
	() => import('@/components/help/MultiEventPanelHelp.vue'),
)
const selectedEventInfoHelp = defineAsyncComponent(
	() => import('@/components/help/SelectedInfoHelp.vue'),
)
const regionControlHelp = defineAsyncComponent(
	() => import('@/components/help/RegionControlHelp.vue'),
)

// Help text entries

export const helpText = {
	eventInfo: {
		title: 'Event Information',
		component: eventInfoHelp,
		target: '#event-info-panel',
		on: 'left',
	},
	timeReel: {
		title: 'Time Reel',
		component: timeReelHelp,
		target: '#time-panel',
		on: 'top',
	},
	hamburgerMenu: {
		title: 'Filters and Settings',
		component: hamburgerMenuHelp,
		target: '#hamburger-menu',
		on: 'left',
	},
	eventDayPanel: {
		title: 'Event Day Panel',
		component: eventDayPanelHelp,
		target: '#event-day-panel',
		on: 'right',
	},
	eventGraphs: {
		title: 'Event Charts',
		component: eventGraphsHelp,
		target: '.event-graphs-help',
		on: 'right',
	},
	multiEventPanel: {
		title: 'Multi-Event Panel',
		component: multiEventPanelHelp,
		target: '#multi-event-panel',
		on: 'left',
	},
	selectedEventInfo: {
		title: 'Selected Event Information',
		component: selectedEventInfoHelp,
		target: '#selected-event-info-panel',
		on: 'right',
	},
	aboutInfo: {
		title: 'About This Tool',
		component: defineAsyncComponent(
			() => import('@/components/help/AboutInfoHelp.vue'),
		),
		icon: IconInfoCircle,
	},
	hardModeUnlocked: {
		title: 'Hard Mode Unlocked!',
		component: defineAsyncComponent(
			() => import('@/components/help/HardModeUnlockedHelp.vue'),
		),
		icon: IconTrophy,
	},
	allComplete: {
		title: 'Master Explorer!',
		component: defineAsyncComponent(
			() => import('@/components/help/AllCompleteHelp.vue'),
		),
		icon: IconRainbow,
	},
	regionControl: {
		title: 'Region Selection',
		component: regionControlHelp,
		target: '#map.region-control',
	},
} as const satisfies Record<string, HelpTextEntry>

// Active help state
export const activeHelp = shallowRef<HelpTextEntry | null>(null)
export const helpMe = (id: keyof typeof helpText) => {
	const helpTextEntry = helpText[id]
	if (!helpTextEntry) {
		console.warn(`No help text found for id: ${id}`)
		console.warn('Available help text ids:', Object.keys(helpText), helpText)
		return
	}
	// Find the parent element to highlight (probably the panel/card)
	activeHelp.value = helpTextEntry
}
export const closeHelp = () => {
	activeHelp.value = null
}
