import Cookies from 'js-cookie'
import { defineStore } from 'pinia'

const ACHIEVEMENTS_COOKIE = 'c3s_achievements'
const VISITS_COOKIE = 'c3s_visits'
const COOKIE_EXPIRY = 365 // days

export interface Achievement {
	id: string
	title: string
	description: string
	icon: string // Tabler icon component name
	color: string // CSS color for completed state
}

export const ACHIEVEMENTS: Achievement[] = [
	{
		id: 'firstVisit',
		title: 'Welcome Aboard',
		description: 'Open the attribution explorer for the first time.',
		icon: 'IconWorld',
		color: 'hsl(211, 57%, 40%)',
	},
	{
		id: 'timeTraveler',
		title: 'Time Traveler',
		description: 'Play the time animation to travel through climate history.',
		icon: 'IconPlayerPlay',
		color: 'hsl(281, 28%, 35%)',
	},
	{
		id: 'pointExplorer',
		title: 'Point Explorer',
		description: 'Click a location on the map to filter events by region.',
		icon: 'IconMapPin',
		color: 'hsl(345, 77%, 33%)',
	},
	{
		id: 'regionScout',
		title: 'Region Scout',
		description: 'Draw a custom region on the map to explore local events.',
		icon: 'IconLassoPolygon',
		color: 'hsl(25, 77%, 33%)',
	},
	{
		id: 'heatwaveWatcher',
		title: 'Heatwave Watcher',
		description: 'Browse extreme heat events across the globe.',
		icon: 'IconFlame',
		color: 'hsl(345, 77%, 33%)',
	},
	{
		id: 'coldFrontChaser',
		title: 'Cold Front Chaser',
		description: 'Browse extreme cold spell events across the globe.',
		icon: 'IconSnowflake',
		color: 'hsl(211, 57%, 40%)',
	},
	{
		id: 'rainChaser',
		title: 'Rain Chaser',
		description: 'Browse extreme precipitation events across the globe.',
		icon: 'IconDroplet',
		color: 'hsl(159, 77%, 33%)',
	},
	{
		id: 'eventInspector',
		title: 'Event Inspector',
		description: 'Focus on a specific extreme weather event for detailed analysis.',
		icon: 'IconZoomIn',
		color: 'hsl(281, 28%, 35%)',
	},
	{
		id: 'bigPicture',
		title: 'Big Picture',
		description: 'Switch to heatmap overview mode to see the full event landscape.',
		icon: 'IconLayoutDashboard',
		color: 'hsl(25, 77%, 33%)',
	},
	{
		id: 'timelineExplorer',
		title: 'Timeline Explorer',
		description: 'Expand the timeline overview to see all events across history.',
		icon: 'IconCalendarStats',
		color: 'hsl(159, 77%, 33%)',
	},
]

interface PersistentState {
	achievements: Record<string, boolean>
	visitCount: number
	lastUnlocked: string | null
}

function loadFromCookies(): PersistentState {
	try {
		const achievementsCookie = Cookies.get(ACHIEVEMENTS_COOKIE)
		const visitsCookie = Cookies.get(VISITS_COOKIE)
		return {
			achievements: achievementsCookie ? JSON.parse(achievementsCookie) : {},
			visitCount: visitsCookie ? parseInt(visitsCookie, 10) : 0,
		}
	} catch {
		return { achievements: {}, visitCount: 0 }
	}
}

export const usePersistentStore = defineStore('persistent', {
	state: (): PersistentState => ({ ...loadFromCookies(), lastUnlocked: null }),
	getters: {
		completedCount: (state) =>
			Object.values(state.achievements).filter(Boolean).length,
	},
	actions: {
		unlockAchievement(id: string) {
			if (!this.achievements[id]) {
				this.achievements[id] = true
				this.lastUnlocked = id
				try {
					Cookies.set(ACHIEVEMENTS_COOKIE, JSON.stringify(this.achievements), {
						expires: COOKIE_EXPIRY,
					})
				} catch {
					// Cookie write failed silently
				}
			}
		},
		incrementVisitCount() {
			this.visitCount++
			try {
				Cookies.set(VISITS_COOKIE, String(this.visitCount), {
					expires: COOKIE_EXPIRY,
				})
			} catch {
				// Cookie write failed silently
			}
		},
	},
})
