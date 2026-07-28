import Cookies from 'js-cookie'
import { defineStore } from 'pinia'

const ACHIEVEMENTS_COOKIE = 'c3s_achievements'
const VISITS_COOKIE = 'c3s_visits'
const HARDMODE_SEEN_COOKIE = 'c3s_hardmode_seen'
const RAINBOW_COOKIE = 'c3s_rainbow'
const ALL_COMPLETE_SEEN_COOKIE = 'c3s_allcomplete_seen'
const COOKIE_EXPIRY = 365 // days

export interface Achievement {
	id: string
	title: string
	description: string
	icon: string // Tabler icon component name
	color: string // CSS color for completed state
}

export interface AchievementSection {
	id: string
	title: string
	sectionIcon: string
	achievements: Achievement[]
}

export const BASIC_ACHIEVEMENTS: Achievement[] = [
	{
		id: 'firstVisit',
		title: 'Welcome Aboard',
		description: 'Open the attribution explorer for the first time.',
		icon: 'IconWorld',
		color: 'hsl(211, 57%, 40%)',
	},
	{
		id: 'timelineExplorer',
		title: 'Timeline Explorer',
		description:
			'Expand the timeline overview to see all events across history.',
		icon: 'IconCalendarWeek',
		color: 'hsl(159, 77%, 33%)',
	},
	{
		id: 'timeTraveler',
		title: 'Time Traveler',
		description: 'Play the time animation to travel through climate history.',
		icon: 'IconPlayerPlay',
		color: 'hsl(281, 28%, 35%)',
	},
	{
		id: 'heatwaveWatcher',
		title: 'Heatwave Hunter',
		description: 'Browse extreme heat events across the globe.',
		icon: 'IconFlame',
		color: 'hsl(345, 77%, 33%)',
	},
	{
		id: 'coldFrontChaser',
		title: 'Cold Spell Chaser',
		description: 'Browse extreme cold spell events across the globe.',
		icon: 'IconSnowflake',
		color: 'hsl(211, 57%, 40%)',
	},
	{
		id: 'rainChaser',
		title: 'Rain Watcher',
		description: 'Browse extreme precipitation events across the globe.',
		icon: 'IconCloudRain',
		color: 'hsl(159, 77%, 33%)',
	},
	{
		id: 'eventInspector',
		title: 'Event Inspector',
		description:
			'Focus on a specific extreme weather event for detailed analysis.',
		icon: 'IconZoomIn',
		color: 'hsl(281, 28%, 35%)',
	},
	{
		id: 'bigPicture',
		title: 'Big Picture',
		description:
			'Switch to overview mode to see the full event landscape.',
		icon: 'IconEye',
		color: 'hsl(25, 77%, 33%)',
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
]

// Hard mode achievements, grouped by site section
export const HARD_ACHIEVEMENT_SECTIONS: AchievementSection[] = [
	{
		id: 'overview',
		title: 'Heatmap Overview',
		sectionIcon: 'IconLayoutDashboard',
		achievements: [
			{
				id: 'hardOverviewHotcold',
				title: 'Dual Threat',
				description:
					'View hot and cold events simultaneously in overview mode.',
				icon: 'IconAdjustments',
				color: 'hsl(281, 28%, 35%)',
			},
			{
				id: 'hardOverviewHotwet',
				title: 'Fire & Rain',
				description: 'View hot and wet events together in overview mode.',
				icon: 'IconCloudRain',
				color: 'hsl(25, 77%, 33%)',
			},
			{
				id: 'hardOverviewColdwet',
				title: 'Arctic Flood',
				description: 'View cold and wet events together in overview mode.',
				icon: 'IconCloudSnow',
				color: 'hsl(185, 67%, 36%)',
			},
			{
				id: 'hardOverviewMaximize',
				title: 'Full Screen',
				description: 'Maximize the multi-event panel.',
				icon: 'IconMaximize',
				color: 'hsl(211, 57%, 40%)',
			},
			{
				id: 'hardOverviewTimeFilter',
				title: 'Time Box',
				description: 'Narrow the time range filter in overview mode.',
				icon: 'IconCalendarSearch',
				color: 'hsl(159, 77%, 33%)',
			},
		],
	},
	{
		id: 'timemachine',
		title: 'Time Machine',
		sectionIcon: 'IconClock',
		achievements: [
			{
				id: 'hardTimemachineEarly',
				title: 'Deep History',
				description: 'Navigate to a date before 1985.',
				icon: 'IconHourglass',
				color: 'hsl(345, 77%, 33%)',
			},
			{
				id: 'hardTimemachineRecent',
				title: 'Present Day',
				description: 'Navigate to a date after 2022.',
				icon: 'IconCalendarEvent',
				color: 'hsl(25, 77%, 33%)',
			},
			{
				id: 'hardTimemachineHot',
				title: 'In the Heat',
				description: 'Select a heat event from the map in Time Machine mode.',
				icon: 'IconSun',
				color: 'hsl(345, 77%, 33%)',
			},
			{
				id: 'hardTimemachineCold',
				title: 'Cold Snap',
				description: 'Select a cold event from the event rankings list in Time Machine mode.',
				icon: 'IconMoon',
				color: 'hsl(211, 57%, 40%)',
			},
			{
				id: 'hardTimemachineWet',
				title: 'Flood Watch',
				description: 'Select a precipitation event from the time reel in Time Machine mode.',
				icon: 'IconCloudStorm',
				color: 'hsl(159, 77%, 33%)',
			},
		],
	},
	{
		id: 'timereel',
		title: 'Time Reel',
		sectionIcon: 'IconTimeline',
		achievements: [
			{
				id: 'hardTimeReelFaster',
				title: 'Fast Forward',
				description: 'Increase the animation playback speed from the settings menu.',
				icon: 'IconPlayerSkipForward',
				color: 'hsl(281, 28%, 35%)',
			},
			{
				id: 'hardTimeReelBarsOff',
				title: 'Clean View',
				description: 'Hide the event bars in the time reel.',
				icon: 'IconChartBarOff',
				color: 'hsl(25, 77%, 33%)',
			},
			{
				id: 'hardTimeReelWindow',
				title: 'Time Window',
				description: 'Set a custom time range filter.',
				icon: 'IconArrowsHorizontal',
				color: 'hsl(159, 77%, 33%)',
			},
		],
	},
	{
		id: 'eventinfo',
		title: 'Events and Rankings',
		sectionIcon: 'IconInfoCircle',
		achievements: [
			{
				id: 'hardEventInfoPanel',
				title: 'Event Briefing',
				description: 'Hide the event information panel.',
				icon: 'IconInfoSquare',
				color: 'hsl(159, 77%, 33%)',
			},
            {
				id: 'hardMultiSortSize',
				title: 'Size Matters',
				description: 'Sort events by geographical size.',
				icon: 'IconArrowsSort',
				color: 'hsl(211, 57%, 40%)',
			},
			{
				id: 'hardMultiSortIntensity',
				title: 'Turn Up the Heat',
				description: 'Sort events by intensity.',
				icon: 'IconChartLine',
				color: 'hsl(345, 77%, 33%)',
			},
			{
				id: 'hardMultiHover',
				title: 'Close Inspection',
				description: 'Hover over an event in the ranked list.',
				icon: 'IconPointer',
				color: 'hsl(25, 77%, 33%)',
			},
			{
				id: 'hardEventDayBrowse',
				title: 'Day by Day',
				description: 'Navigate to a specific day within an event.',
				icon: 'IconCalendarTime',
				color: 'hsl(211, 57%, 40%)',
			},
		],
	},
	{
		id: 'settings',
		title: 'Settings Menu',
		sectionIcon: 'IconMenu2',
		achievements: [
			{
				id: 'hardHamburgerOpen',
				title: 'Settings Seeker',
				description: 'Open the settings and filter menu.',
				icon: 'IconSettings',
				color: 'hsl(345, 77%, 33%)',
			},
			{
				id: 'hardHamburgerDurationFilter',
				title: 'Fine Tuning',
				description: 'Adjust the minimum event duration filter.',
				icon: 'IconFilter',
				color: 'hsl(281, 28%, 35%)',
			},
			{
				id: 'hardHamburgerIntensityFilter',
				title: 'Intensity Threshold',
				description: 'Change the sense (greater than/less than) of the temperature/precipitation filter.',
				icon: 'IconGauge',
				color: 'hsl(25, 77%, 33%)',
			},
		],
	},
]

export const HARD_ACHIEVEMENTS: Achievement[] =
	HARD_ACHIEVEMENT_SECTIONS.flatMap((s) => s.achievements)

export const RAINBOW_ACHIEVEMENT: Achievement = {
	id: 'rainbowMode',
	title: 'Rainbow Mode',
	description: 'Enable rainbow mode from the settings menu.',
	icon: 'IconRainbow',
	color: 'hsl(300, 70%, 50%)',
}

// Backwards-compatible export
export const ACHIEVEMENTS = BASIC_ACHIEVEMENTS

interface PersistentState {
	achievements: Record<string, boolean>
	visitCount: number
	lastUnlocked: string | null
	hardModeSeen: boolean
	rainbowMode: boolean
	allCompleteSeen: boolean
}

function loadFromCookies(): PersistentState {
	try {
		const achievementsCookie = Cookies.get(ACHIEVEMENTS_COOKIE)
		const visitsCookie = Cookies.get(VISITS_COOKIE)
		const hardModeSeen = Cookies.get(HARDMODE_SEEN_COOKIE) === '1'
		const rainbowMode = Cookies.get(RAINBOW_COOKIE) === '1'
		const allCompleteSeen = Cookies.get(ALL_COMPLETE_SEEN_COOKIE) === '1'
		return {
			achievements: achievementsCookie ? JSON.parse(achievementsCookie) : {},
			visitCount: visitsCookie ? parseInt(visitsCookie, 10) : 0,
			hardModeSeen,
			rainbowMode,
			allCompleteSeen,
			lastUnlocked: null,
		}
	} catch {
		return {
			achievements: {},
			visitCount: 0,
			hardModeSeen: false,
			rainbowMode: false,
			allCompleteSeen: false,
			lastUnlocked: null,
		}
	}
}

export const usePersistentStore = defineStore('persistent', {
	state: (): PersistentState => ({ ...loadFromCookies(), lastUnlocked: null }),
	getters: {
		completedCount: (state) =>
			Object.values(state.achievements).filter(Boolean).length,
		nBasicComplete: (state) =>
			BASIC_ACHIEVEMENTS.filter((a) => state.achievements[a.id]).length,
		basicComplete: (state) =>
			BASIC_ACHIEVEMENTS.every((a) => state.achievements[a.id]),
		hardModeUnlocked: (state) =>
			BASIC_ACHIEVEMENTS.every((a) => state.achievements[a.id]),
		allHardComplete: (state) =>
			[...BASIC_ACHIEVEMENTS, ...HARD_ACHIEVEMENTS].every((a) => state.achievements[a.id]),
		allComplete: (state) =>
			[...BASIC_ACHIEVEMENTS, ...HARD_ACHIEVEMENTS, RAINBOW_ACHIEVEMENT].every(
				(a) => state.achievements[a.id],
			),
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
		setHardModeSeen() {
			this.hardModeSeen = true
			try {
				Cookies.set(HARDMODE_SEEN_COOKIE, '1', { expires: COOKIE_EXPIRY })
			} catch {
				// Cookie write failed silently
			}
		},
		setRainbowMode(on: boolean) {
			this.rainbowMode = on
			try {
				Cookies.set(RAINBOW_COOKIE, on ? '1' : '0', {
					expires: COOKIE_EXPIRY,
				})
			} catch {
				// Cookie write failed silently
			}
			if (on) {
				this.unlockAchievement('rainbowMode')
			}
		},
		setAllCompleteSeen() {
			this.allCompleteSeen = true
			try {
				Cookies.set(ALL_COMPLETE_SEEN_COOKIE, '1', { expires: COOKIE_EXPIRY })
			} catch {
				// Cookie write failed silently
			}
		},
	},
})
