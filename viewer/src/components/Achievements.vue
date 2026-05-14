<script setup lang="ts">
import { computed, ref } from 'vue'
import {
	usePersistentStore,
	BASIC_ACHIEVEMENTS,
	HARD_ACHIEVEMENT_SECTIONS,
	HARD_ACHIEVEMENTS,
	RAINBOW_ACHIEVEMENT,
} from '@/store/persistentStore'
import {
	IconWorld,
	IconPlayerPlay,
	IconMapPin,
	IconLassoPolygon,
	IconFlame,
	IconSnowflake,
	IconZoomIn,
	IconLayoutDashboard,
	IconCalendarWeek,
	IconTrophy,
	IconLock,
	// Hard mode icons
	IconAdjustments,
	IconCloudRain,
	IconCloudSnow,
	IconMaximize,
	IconCalendarSearch,
	IconClock,
	IconHourglass,
	IconCalendarEvent,
	IconSun,
	IconMoon,
	IconCloudStorm,
	IconTimeline,
	IconPlayerSkipForward,
	IconChartBarOff,
	IconArrowsHorizontal,
	IconListDetails,
	IconArrowsSort,
	IconChartLine,
	IconReportAnalytics,
	IconPointer,
	IconInfoCircle,
	IconInfoSquare,
	IconCalendarTime,
	IconMenu2,
	IconSettings,
	IconFilter,
	IconGauge,
    IconEye,
	// Rainbow
	IconRainbow,
} from '@tabler/icons-vue'

import Cookies from 'js-cookie'

const persistentStore = usePersistentStore()

const isDev = import.meta.env.DEV

const resetAchievements = () => {
	persistentStore.achievements = {}
	persistentStore.visitCount = 0
	persistentStore.lastUnlocked = null
	persistentStore.hardModeSeen = false
	persistentStore.rainbowMode = false
	Cookies.remove('c3s_achievements')
	Cookies.remove('c3s_visits')
	Cookies.remove('c3s_hardmode_seen')
	Cookies.remove('c3s_rainbow')
}

const resetPreRainbow = () => {
	const updated = { ...persistentStore.achievements }
	delete updated['rainbowMode']
	delete updated['hardEventInfoPanel']
	persistentStore.achievements = updated
	persistentStore.rainbowMode = false
	Cookies.set('c3s_achievements', JSON.stringify(updated), { expires: 365 })
	Cookies.remove('c3s_rainbow')
}

const iconComponents: Record<string, unknown> = {
	IconWorld,
	IconPlayerPlay,
	IconMapPin,
	IconLassoPolygon,
	IconFlame,
	IconSnowflake,
	IconCloudRain,
	IconZoomIn,
	IconLayoutDashboard,
	IconCalendarWeek,
	// Hard mode icons
	IconAdjustments,
	IconCloudRain,
	IconCloudSnow,
	IconMaximize,
	IconCalendarSearch,
	IconClock,
	IconHourglass,
	IconCalendarEvent,
	IconSun,
	IconMoon,
	IconCloudStorm,
	IconTimeline,
	IconPlayerSkipForward,
	IconChartBarOff,
	IconArrowsHorizontal,
	IconListDetails,
	IconArrowsSort,
	IconChartLine,
	IconReportAnalytics,
	IconPointer,
	IconInfoCircle,
	IconInfoSquare,
	IconCalendarTime,
	IconMenu2,
	IconSettings,
	IconFilter,
	IconGauge,
    IconEye,
	// Rainbow
	IconRainbow,
}

const basicCollapsed = ref(true)
const hardCollapsed = ref(false)

const sortedBasic = computed(() => {
	const completed = BASIC_ACHIEVEMENTS.filter((a) => persistentStore.achievements[a.id])
	const pending = BASIC_ACHIEVEMENTS.filter((a) => !persistentStore.achievements[a.id])
	return [...completed, ...pending]
})

const totalCount = computed(() => {
	const base = BASIC_ACHIEVEMENTS.length
	const hard = persistentStore.hardModeUnlocked ? HARD_ACHIEVEMENTS.length : 0
	const rainbow = persistentStore.allHardComplete ? 1 : 0
	return base + hard + rainbow
})
</script>

<template>
	<div class="achievements-panel">
		<div class="achievements-header">
			<IconTrophy size="20" aria-hidden="true" />
			<h2>Achievements</h2>
			<span class="count">{{ persistentStore.nBasicComplete }} / {{ totalCount }}</span>
		</div>

		<!-- Basic achievements (shown at top until hard mode; collapses to bottom once unlocked) -->
		<button v-if="persistentStore.hardModeUnlocked" class="hard-mode-header" @click="basicCollapsed = !basicCollapsed">
			<IconTrophy size="16" class="hard-mode-icon" aria-hidden="true" />
			<span>Basics ({{ BASIC_ACHIEVEMENTS.length }}/{{ BASIC_ACHIEVEMENTS.length }})</span>
			<span class="collapse-chevron" :class="{ open: !basicCollapsed }">▸</span>
		</button>
		<ul
			v-if="!persistentStore.hardModeUnlocked || !basicCollapsed"
			class="achievements-list"
			:class="{ 'basics-collapsed': persistentStore.hardModeUnlocked }"
		>
			<li
				v-for="achievement in sortedBasic"
				:key="achievement.id"
				class="achievement-item"
				:class="{ completed: persistentStore.achievements[achievement.id] || persistentStore.hardModeUnlocked }"
			>
				<div
					class="achievement-icon"
					:style="(persistentStore.achievements[achievement.id] || persistentStore.hardModeUnlocked) ? { color: achievement.color } : {}"
				>
					<component
						:is="iconComponents[achievement.icon]"
						v-if="persistentStore.achievements[achievement.id] || persistentStore.hardModeUnlocked"
						size="22"
						aria-hidden="true"
					/>
					<IconLock v-else size="22" aria-hidden="true" />
				</div>
				<div class="achievement-text">
					<span class="achievement-title">{{ achievement.title }}</span>
					<span class="achievement-desc">{{ achievement.description }}</span>
				</div>
			</li>
		</ul>

		<!-- Hard mode sections (revealed when basic achievements complete) -->
		<template v-if="persistentStore.hardModeUnlocked">
			<button class="hard-mode-header" @click="hardCollapsed = !hardCollapsed">
				<IconTrophy size="16" class="hard-mode-icon" aria-hidden="true" />
				<span>Hard Mode</span>
				<span class="collapse-chevron" :class="{ open: !hardCollapsed }">▸</span>
			</button>

			<template v-if="!hardCollapsed" v-for="section in HARD_ACHIEVEMENT_SECTIONS" :key="section.id">
				<div class="section-header">
					<component :is="iconComponents[section.sectionIcon]" size="14" aria-hidden="true" />
					<span>{{ section.title }}</span>
				</div>
				<ul class="achievements-list">
					<li
						v-for="achievement in section.achievements"
						:key="achievement.id"
						class="achievement-item"
						:class="{ completed: persistentStore.achievements[achievement.id] }"
					>
						<div
							class="achievement-icon"
							:style="persistentStore.achievements[achievement.id] ? { color: achievement.color } : {}"
						>
							<component
								:is="iconComponents[achievement.icon]"
								v-if="persistentStore.achievements[achievement.id]"
								size="22"
								aria-hidden="true"
							/>
							<IconLock v-else size="22" aria-hidden="true" />
						</div>
						<div class="achievement-text">
							<span class="achievement-title">{{ achievement.title }}</span>
							<span class="achievement-desc">{{ achievement.description }}</span>
						</div>
					</li>
				</ul>
			</template>
		</template>

		<!-- Rainbow achievement (revealed when all hard mode achievements complete) -->
		<template v-if="persistentStore.allHardComplete">
			<div class="hard-mode-header rainbow">
				<IconRainbow size="16" class="rainbow-icon" aria-hidden="true" />
				<span>Final Challenge</span>
			</div>
			<ul class="achievements-list">
				<li
					class="achievement-item"
					:class="{ completed: persistentStore.achievements[RAINBOW_ACHIEVEMENT.id] }"
				>
					<div
						class="achievement-icon"
						:style="persistentStore.achievements[RAINBOW_ACHIEVEMENT.id] ? { color: RAINBOW_ACHIEVEMENT.color } : {}"
					>
						<IconRainbow
							v-if="persistentStore.achievements[RAINBOW_ACHIEVEMENT.id]"
							size="22"
							aria-hidden="true"
						/>
						<IconLock v-else size="22" aria-hidden="true" />
					</div>
					<div class="achievement-text">
						<span class="achievement-title">{{ RAINBOW_ACHIEVEMENT.title }}</span>
						<span class="achievement-desc">{{ RAINBOW_ACHIEVEMENT.description }}</span>
					</div>
				</li>
			</ul>
		</template>

		<button v-if="isDev" class="reset-button" @click="resetAchievements">Reset achievements</button>
		<button v-if="isDev" class="reset-button" @click="resetPreRainbow">Reset pre-rainbow</button>


	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.achievements-panel {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
	min-width: 260px;
	max-width: 320px;
    height: 100%;
    max-height: 100%;
    flex: 0 0 100%;
    overflow-y: hidden;
}

.achievements-header {
	position: sticky;
	top: 0;
	z-index: 1;
	background: var(--panel-bg);
	padding-bottom: 0.25rem;
	margin-bottom: -0.25rem;
	display: flex;
	align-items: center;
	gap: 0.5rem;

	h2 {
		font-size: 1rem;
		margin: 0.25rem 0 0 0;
		flex: 1;
	}

	.count {
		font-size: 0.8rem;
		opacity: 0.6;
		font-variant-numeric: tabular-nums;
		margin-right: 2 * $panelMargin;
	}
}

.hard-mode-header {
	display: flex;
	align-items: center;
	gap: 0.375rem;
	margin-top: 0.5rem;
	padding: 0.375rem 0 0.125rem 0;
	border-top: 1px solid var(--divider);
	font-size: 0.8rem;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	opacity: 0.8;

	&:is(button) {
		width: 100%;
		border: none;
		border-top: 1px solid var(--divider);
		background: none;
		cursor: pointer;
		color: inherit;
		text-align: left;
		transition: opacity $animTime $animEase;

		&:hover {
			opacity: 1;
		}
	}

	.hard-mode-icon {
		color: $lightbulb;
	}

	&.rainbow .rainbow-icon {
		color: hsl(300, 70%, 50%);
	}

	.collapse-chevron {
		margin-left: auto;
		transition: transform $animTime $animEase;
		transform: rotate(0deg);

		&.open {
			transform: rotate(90deg);
		}
	}
}

.section-header {
	display: flex;
	align-items: center;
	gap: 0.25rem;
	margin-top: 0.375rem;
	font-size: 0.7rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	opacity: 0.5;
}

.achievements-list {
    list-style: none;
	padding: 0;
	margin: 0;
	display: flex;
	flex-direction: column;
	gap: 0.375rem;
}

.achievement-item {
	display: flex;
	align-items: flex-start;
	gap: 0.625rem;
	padding: 0.375rem 0;
	border-radius: 6px;
	opacity: 0.4;
	transition: opacity $animTime $animEase;

	&.completed {
		opacity: 1;
	}
}

.achievement-icon {
	flex-shrink: 0;
	color: var(--text-tertiary);
	margin-top: 1px;
}

.achievement-text {
	display: flex;
	flex-direction: column;
	gap: 0.125rem;
}

.achievement-title {
	font-size: 0.875rem;
	font-weight: 600;
	line-height: 1.2;
}

.achievement-desc {
	font-size: 0.75rem;
	opacity: 0.65;
	line-height: 1.3;
}

.reset-button {
	margin-top: 0.5rem;
	padding: 0.25rem 0.625rem;
	font-size: 0.7rem;
	opacity: 0.4;
	border: 1px dashed currentColor;
	border-radius: 4px;
	background: none;
	cursor: pointer;
	color: inherit;
	transition: opacity $animTime $animEase;
	align-self: flex-start;

	&:hover {
		opacity: 0.8;
	}
}

.collapse-header {
	display: flex;
	align-items: center;
	gap: 0.375rem;
	width: 100%;
	margin-top: 0.5rem;
	padding: 0.375rem 0 0.125rem 0;
	border: none;
	border-top: 1px solid var(--divider);
	background: none;
	cursor: pointer;
	font-size: 0.7rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: inherit;
	opacity: 0.5;
	text-align: left;
	transition: opacity $animTime $animEase;

	&:hover {
		opacity: 0.8;
	}

	span {
		flex: 1;
	}

	.collapse-chevron {
		flex: 0;
		transition: transform $animTime $animEase;
		transform: rotate(0deg);

		&.open {
			transform: rotate(90deg);
		}
	}
}

.basics-collapsed {
	opacity: 0.7;
}
</style>
