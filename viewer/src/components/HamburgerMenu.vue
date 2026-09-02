<script setup lang="ts">
import { computed, ref } from 'vue'
import { useStore } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import { usePersistentStore } from '@/store/persistentStore'
import { useUserRegionsStore, MAX_USER_REGIONS } from '@/store/userRegionsStore'
import { validateUserRegion } from '@/lib/validateGeoJson'
import { useLabels } from '@/lib/labels'
import EventTypeToggle from './util/EventTypeToggle.vue'
import FilterPanel from './FilterPanel.vue'
import {
	IconMenu2,
	IconX,
	IconRainbow,
	IconPlayerPlay,
	IconPlayerTrackNext,
	IconUpload,
	IconTrash,
	IconPolygon,
	IconRocket,
} from '@tabler/icons-vue'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()
const persistentStore = usePersistentStore()
const userRegionsStore = useUserRegionsStore()

const SPEEDS = [0.25, 0.5, 1, 2, 4]

const speedIndex = computed(() => {
	const i = SPEEDS.indexOf(timeStore.speedFactor)
	return i >= 0 ? i : 2 // default to index 2 = 1×
})

const onSpeedInput = (e: Event) => {
	timeStore.speedFactor = SPEEDS[Number((e.target as HTMLInputElement).value)]
}

// The intro resets itself when it opens, so the menu only has to get out of
// the way and flip the flag.
const replayIntro = () => {
	store.hamburgerMenuOpen = false
	store.onboardingOpen = true
}

// --- User regions ---

const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref<string | null>(null)
const uploadWarning = ref<string | null>(null)
let errorTimer: ReturnType<typeof setTimeout> | null = null

// Merge UI state
const pendingMergeData = ref<UserRegion | null>(null)
const mergeTargetId = ref<string>('')

const triggerUpload = () => {
	uploadError.value = null
	uploadWarning.value = null
	pendingMergeData.value = null
	fileInput.value?.click()
}

const showError = (msg: string) => {
	uploadError.value = msg
	uploadWarning.value = null
	if (errorTimer) clearTimeout(errorTimer)
	errorTimer = setTimeout(() => { uploadError.value = null }, 4000)
}

const onFileSelected = (e: Event) => {
	const file = (e.target as HTMLInputElement).files?.[0]
	if (!file) return
	// Reset so the same file can be re-selected after an error
	;(e.target as HTMLInputElement).value = ''

	const reader = new FileReader()
	reader.onload = async () => {
		// Validation simplifies large geometries — show the loading overlay so a
		// big file doesn't appear to freeze the UI while it's processed.
		await store.setLoading('Processing region...')
		try {
			const result = validateUserRegion(reader.result as string, file.name)
			if (!result.valid) {
				showError(result.error)
				return
			}
			if (result.warning) {
				uploadWarning.value = result.warning
			}
			if (userRegionsStore.regions.length >= MAX_USER_REGIONS) {
				// Offer merge
				pendingMergeData.value = result.data
				mergeTargetId.value = userRegionsStore.regions[0]?.id ?? ''
			} else {
				if (!userRegionsStore.addRegion(result.data)) {
					showError($l.value.uploadErrorTooLarge)
				}
			}
		} finally {
			store.setLoadingDone()
		}
	}
	reader.readAsText(file)
}

const confirmMerge = () => {
	if (!pendingMergeData.value || !mergeTargetId.value) return
	const ok = userRegionsStore.mergeIntoRegion(
		mergeTargetId.value,
		pendingMergeData.value.geojson,
	)
	pendingMergeData.value = null
	if (!ok) {
		showError($l.value.uploadErrorTooLarge)
	}
}

const cancelMerge = () => {
	pendingMergeData.value = null
	uploadWarning.value = null
}

const featureLabel = (region: UserRegion) => {
	if (region.geojson.type === 'Feature') return '1 polygon'
	const n = region.geojson.features.length
	return `${n} polygon${n === 1 ? '' : 's'}`
}
</script>

<template>
	<!-- Hamburger menu button -->
	<button
		id="hamburger-button"
		class="glassy color"
		:class="{
			hidden: store.isFocused || timeStore.timePanelExpanded,
			close: store.hamburgerMenuOpen,
		}"
		:inert="
			store.isFocused || timeStore.timePanelExpanded ? 'true' : undefined
		"
		@click="store.hamburgerMenuOpen = !store.hamburgerMenuOpen"
		v-tooltip="store.hamburgerMenuOpen ? $l.close : $l.hamburger"
	>
		<IconMenu2 size="24" aria-hidden="true" v-if="!store.hamburgerMenuOpen" />
		<IconX size="24" aria-hidden="true" v-else />
	</button>

	<!-- Hamburger menu panel -->
	<div
		id="hamburger-menu"
		class="panel top"
		:class="{ active: store.hamburgerMenuOpen && !store.isFocused }"
		:inert="!store.hamburgerMenuOpen ? 'true' : undefined"
	>
		<div class="menu-section">
			<h2>{{ $l.chooseEventType }}</h2>
			<EventTypeToggle
				:model-value="eventStore.eventTypeMode"
				@update:model-value="eventStore.setEventTypeMode"
			/>
		</div>
		<div class="menu-section">
			<h2>{{ $l.chooseFilters }}</h2>
			<FilterPanel v-model="eventStore.filters" />
		</div>
		<div class="menu-section speed-section">
			<h2>Animation Speed</h2>
			<div class="speed-row">
				<IconPlayerPlay class="speed-icon" :size="16" aria-hidden="true" />
				<div class="speed-slider-wrap">
					<input
						type="range"
						class="speed-slider"
						min="0"
						max="4"
						step="1"
						:value="speedIndex"
						@input="onSpeedInput"
					/>
					<div class="speed-ticks" aria-hidden="true">
						<span v-for="i in 5" :key="i" class="tick" />
					</div>
				</div>
				<IconPlayerTrackNext class="speed-icon" :size="16" aria-hidden="true" />
			</div>
		</div>
		<div class="menu-section intro-section">
			<button class="intro-btn" @click="replayIntro">
				<IconRocket :size="15" aria-hidden="true" />
				{{ $l.replayIntro }}
			</button>
		</div>
		<div v-if="persistentStore.allHardComplete" class="menu-section rainbow-section">
			<h2>Rainbow Mode</h2>
			<button
				class="rainbow-toggle"
				:class="{ active: persistentStore.rainbowMode }"
				@click="persistentStore.setRainbowMode(!persistentStore.rainbowMode)"
			>
				<IconRainbow size="18" aria-hidden="true" />
				{{ persistentStore.rainbowMode ? 'Disable' : 'Enable' }} Rainbow Mode
			</button>
		</div>

		<!-- Your Regions section -->
		<div class="menu-section regions-section">
			<h2>{{ $l.yourRegions }}</h2>

			<!-- Hidden file input -->
			<input
				ref="fileInput"
				type="file"
				accept=".geojson,.json"
				style="display: none"
				@change="onFileSelected"
			/>

			<!-- Upload button -->
			<button
				class="upload-btn"
				:disabled="!!pendingMergeData"
				@click="triggerUpload"
				v-tooltip="$l.uploadRegionTooltip"
			>
				<IconUpload :size="15" aria-hidden="true" />
				{{ $l.uploadRegion }}
			</button>

			<!-- Feedback messages -->
			<p v-if="uploadError" class="region-feedback region-feedback--error" @click="uploadError = null">
				{{ uploadError }}
			</p>
			<p v-if="uploadWarning && !pendingMergeData" class="region-feedback region-feedback--warning" @click="uploadWarning = null">
				{{ uploadWarning }}
			</p>

			<!-- Merge UI -->
			<div v-if="pendingMergeData" class="merge-panel">
				<p class="merge-label">{{ $l.regionLimitReached }}</p>
				<p v-if="uploadWarning" class="region-feedback region-feedback--warning">{{ uploadWarning }}</p>
				<div class="merge-row">
					<label class="merge-select-label">{{ $l.mergeIntoRegion }}</label>
					<select v-model="mergeTargetId" class="merge-select">
						<option
							v-for="r in userRegionsStore.regions"
							:key="r.id"
							:value="r.id"
						>{{ r.name }}</option>
					</select>
				</div>
				<div class="merge-actions">
					<button class="merge-btn merge-btn--confirm" @click="confirmMerge">{{ $l.mergeConfirm }}</button>
					<button class="merge-btn merge-btn--cancel" @click="cancelMerge">{{ $l.mergeCancel }}</button>
				</div>
			</div>

			<!-- Saved region list -->
			<ul v-if="userRegionsStore.regions.length" class="region-list">
				<li
					v-for="region in userRegionsStore.regions"
					:key="region.id"
					class="region-item"
					:class="{ active: userRegionsStore.activeRegionId === region.id }"
				>
					<span
						v-if="region.geojson.type === 'FeatureCollection' && region.geojson.features.length > 1"
						class="region-icon region-icon--multi"
						aria-hidden="true"
					>
						<IconPolygon class="poly-back" :size="14" />
						<IconPolygon class="poly-front" :size="14" />
					</span>
					<span v-else class="region-icon" aria-hidden="true">
						<IconPolygon :size="14" />
					</span>
					<span class="region-name" v-tooltip="region.name">{{ region.name }}</span>
					<span class="region-count">{{ featureLabel(region) }}</span>
					<button
						class="region-delete"
						:aria-label="`${$l.deleteRegion}: ${region.name}`"
						v-tooltip="$l.deleteRegion"
						@click="userRegionsStore.deleteRegion(region.id)"
					>
						<IconTrash :size="14" aria-hidden="true" />
					</button>
				</li>
			</ul>
		</div>
	</div>
</template>

<style lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.main {
	#hamburger-button {
		position: absolute;
		top: $panelMargin;
		right: $panelMargin;
		border-radius: 100%;
		width: 2.5rem;
		height: 2.5rem;
		padding: 0.5rem;
		z-index: 400;
		box-shadow: var(--shadow-sm), var(--shadow-md);

		&.hidden {
			transform: translateY(-200%);
		}
	}

	#hamburger-menu {
		background: var(--panel-bg);
		backdrop-filter: $frosty;
		top: $panelMargin;
		right: $panelMargin;
		padding: $panelMargin * 0.5;
		display: flex;
		flex-direction: column;
		justify-content: stretch;
		align-items: stretch;
		gap: $panelMargin * 0.5;
		z-index: 350;

		.menu-section {
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
			padding: 0;

			h2 {
				font-size: 1rem;
				margin: 0.25rem 0 0 0;
			}
		}

		.speed-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.speed-row {
			display: flex;
			align-items: center;
			gap: 0.5rem;
		}

		.speed-icon {
			flex-shrink: 0;
			opacity: 0.55;
		}

		.speed-slider-wrap {
			flex: 1;
			display: flex;
			flex-direction: column;
			gap: 3px;
		}

		.speed-slider {
			width: 100%;
			appearance: none;
			-webkit-appearance: none;
			height: 4px;
			border-radius: 2px;
			background: var(--divider);
			outline: none;
			cursor: pointer;
			accent-color: var(--primary);

			&::-webkit-slider-thumb {
				-webkit-appearance: none;
				width: 14px;
				height: 14px;
				border-radius: 50%;
				background: var(--primary);
				cursor: pointer;
				border: none;
			}

			&::-moz-range-thumb {
				width: 14px;
				height: 14px;
				border-radius: 50%;
				background: var(--primary);
				cursor: pointer;
				border: none;
			}
		}

		.speed-ticks {
			display: flex;
			justify-content: space-between;
			padding: 0 7px; // half of 14px thumb width — aligns ticks under thumb centres

			.tick {
				width: 1px;
				height: 4px;
				background: var(--text-tertiary);
				opacity: 0.4;
				border-radius: 1px;
			}
		}

		.intro-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.intro-btn {
			display: flex;
			align-items: center;
			gap: 0.4rem;
			padding: 0.375rem 0.75rem;
			border-radius: 6px;
			border: 1px solid var(--divider);
			background: none;
			cursor: pointer;
			font-size: 0.875rem;
			color: inherit;
			transition: background $animTime $animEase;

			&:hover {
				background: var(--hover-bg, rgba(0, 0, 0, 0.06));
			}
		}

		.rainbow-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.rainbow-toggle {
			display: flex;
			align-items: center;
			gap: 0.5rem;
			padding: 0.375rem 0.75rem;
			border-radius: 6px;
			border: 1px solid var(--divider);
			background: none;
			cursor: pointer;
			font-size: 0.875rem;
			color: inherit;
			transition: background $animTime $animEase, color $animTime $animEase;

			&.active {
				background: linear-gradient(100deg, $c3sred, $c3sorange, $lightbulb, $c3sgreen, $c3steal, $c3sblue, $c3spurple);
				color: white;
				border-color: transparent;
			}
		}

		.regions-section {
			border-top: 1px solid var(--divider);
			padding-top: 0.5rem;
		}

		.upload-btn {
			display: flex;
			align-items: center;
			gap: 0.4rem;
			padding: 0.375rem 0.75rem;
			border-radius: 6px;
			border: 1px solid var(--divider);
			background: none;
			cursor: pointer;
			font-size: 0.875rem;
			color: inherit;
			transition: background $animTime $animEase;

			&:hover:not(:disabled) {
				background: var(--hover-bg, rgba(0, 0, 0, 0.06));
			}
			&:disabled {
				opacity: 0.45;
				cursor: default;
			}
		}

		.region-feedback {
			font-size: 0.8rem;
			border-radius: 4px;
			padding: 0.3rem 0.5rem;
			margin: 0;
			cursor: pointer;

			&--error {
				background: rgba(200, 40, 40, 0.12);
				color: $c3sred;
			}
			&--warning {
				background: rgba(200, 140, 0, 0.12);
				color: $c3sorange;
			}
		}

		.merge-panel {
			display: flex;
			flex-direction: column;
			gap: 0.4rem;
			padding: 0.5rem;
			border-radius: 6px;
			border: 1px solid var(--divider);
			background: var(--hover-bg, rgba(0, 0, 0, 0.04));
		}

		.merge-label {
			font-size: 0.8rem;
			margin: 0;
			opacity: 0.8;
		}

		.merge-row {
			display: flex;
			align-items: center;
			gap: 0.4rem;
		}

		.merge-select-label {
			font-size: 0.8rem;
			white-space: nowrap;
			flex-shrink: 0;
		}

		.merge-select {
			flex: 1;
			font-size: 0.8rem;
			border: 1px solid var(--divider);
			border-radius: 4px;
			padding: 0.2rem 0.3rem;
			background: var(--panel-bg);
			color: inherit;
			min-width: 0;
		}

		.merge-actions {
			display: flex;
			gap: 0.4rem;
		}

		.merge-btn {
			flex: 1;
			padding: 0.3rem 0.5rem;
			border-radius: 4px;
			border: 1px solid var(--divider);
			font-size: 0.8rem;
			cursor: pointer;
			background: none;
			color: inherit;

			&--confirm {
				background: var(--primary);
				color: white;
				border-color: transparent;
			}
			&--cancel {
				opacity: 0.7;
			}
		}

		.region-list {
			list-style: none;
			margin: 0;
			padding: 0;
			display: flex;
			flex-direction: column;
			gap: 2px;
		}

		.region-item {
			display: flex;
			align-items: center;
			gap: 0.35rem;
			padding: 0.3rem 0.4rem;
			border-radius: 5px;
			border: 1px solid transparent;
			font-size: 0.8rem;
			transition: background $animTime $animEase;

			&.active {
				background: rgba(var(--primary-rgb, 30, 100, 200), 0.1);
				border-color: rgba(var(--primary-rgb, 30, 100, 200), 0.25);
			}

			.region-icon {
				flex-shrink: 0;
				opacity: 0.6;
				display: flex;
				align-items: center;
			}

			.region-icon--multi {
				position: relative;
				width: 16px;
				height: 16px;

				.poly-back,
				.poly-front {
					position: absolute;
				}

				.poly-back {
					top: 0;
					left: 0;
					opacity: 0.5;
				}

				.poly-front {
					bottom: 0;
					right: 0;
				}
			}

			.region-name {
				flex: 1;
				min-width: 0;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			.region-count {
				flex-shrink: 0;
				opacity: 0.5;
				font-size: 0.75rem;
			}

			.region-delete {
				flex-shrink: 0;
				background: none;
				border: none;
				padding: 0.15rem;
				cursor: pointer;
				color: inherit;
				opacity: 0.45;
				display: flex;
				align-items: center;
				border-radius: 3px;
				transition: opacity $animTime $animEase, background $animTime $animEase;

				&:hover {
					opacity: 1;
					background: rgba(200, 40, 40, 0.12);
					color: $c3sred;
				}
			}
		}
	}
}
</style>
