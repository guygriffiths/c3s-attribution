<script setup lang="ts">
import { computed } from 'vue'
import { usePersistentStore, ACHIEVEMENTS } from '@/store/persistentStore'
import { useStore as useMainStore } from '@/store/store'
import {
	IconWorld,
	IconPlayerPlay,
	IconMapPin,
	IconLassoPolygon,
	IconFlame,
	IconSnowflake,
	IconDroplet,
	IconZoomIn,
	IconLayoutDashboard,
	IconCalendarStats,
	IconTrophy,
	IconLock,
} from '@tabler/icons-vue'

import Cookies from 'js-cookie'

const persistentStore = usePersistentStore()
const mainStore = useMainStore()

const isDev = import.meta.env.DEV

const resetAchievements = () => {
	persistentStore.achievements = {}
	persistentStore.visitCount = 0
	persistentStore.lastUnlocked = null
	Cookies.remove('c3s_achievements')
	Cookies.remove('c3s_visits')
}

const iconComponents: Record<string, unknown> = {
	IconWorld,
	IconPlayerPlay,
	IconMapPin,
	IconLassoPolygon,
	IconFlame,
	IconSnowflake,
	IconDroplet,
	IconZoomIn,
	IconLayoutDashboard,
	IconCalendarStats,
}

const sortedAchievements = computed(() => {
	const completed = ACHIEVEMENTS.filter(
		(a) => persistentStore.achievements[a.id],
	)
	const pending = ACHIEVEMENTS.filter((a) => !persistentStore.achievements[a.id])
	return [...completed, ...pending]
})
</script>

<template>
	<div class="achievements-panel">
		<div class="achievements-header">
			<IconTrophy size="20" aria-hidden="true" />
			<h2>Achievements</h2>
			<span class="count">{{ persistentStore.completedCount }} / {{ ACHIEVEMENTS.length }}</span>
		</div>

		<p class="visit-count">Visits: {{ persistentStore.visitCount }}</p>

		<ul class="achievements-list">
			<li
				v-for="achievement in sortedAchievements"
				:key="achievement.id"
				class="achievement-item"
				:class="{ completed: persistentStore.achievements[achievement.id] }"
			>
				<div
					class="achievement-icon"
					:style="
						persistentStore.achievements[achievement.id]
							? { color: achievement.color }
							: {}
					"
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

		<button v-if="isDev" class="reset-button" @click="resetAchievements">Reset achievements</button>
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
}

.achievements-header {
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
        margin-right: 2*$panelMargin;
	}
}

.visit-count {
	font-size: 0.75rem;
	opacity: 0.5;
	margin: 0;
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
</style>
