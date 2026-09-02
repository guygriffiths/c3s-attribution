<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { format } from 'date-fns'
import {
	IconCalendarTime,
	IconChevronLeft,
	IconChevronRight,
	IconCloudRain,
	IconEyePin,
	IconPointer,
	IconRocket,
	IconTemperatureSnow,
	IconTemperatureSun,
	IconWorldSearch,
	IconX,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'
import type { IntroButton } from '@/store/store'
import { useStore as useTimeStore } from '@/store/timeStore'
import { useStore as useEventStore } from '@/store/eventStore'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
const store = useStore()
const timeStore = useTimeStore()
const eventStore = useEventStore()

// One icon per step, paired up with the text in labels.introSteps.
const STEP_ICONS = [
	IconWorldSearch,
	IconCalendarTime,
	IconEyePin,
	IconPointer,
	IconRocket,
]

// Only the three single types are offered here. The combinations are a
// refinement, and they stay on the wheel in the menu.
const EVENT_TYPES = [
	{ id: 'hot', icon: IconTemperatureSun },
	{ id: 'cold', icon: IconTemperatureSnow },
	{ id: 'wet', icon: IconCloudRain },
] as const

const step = ref(0)

// The record stops short of today, so take the headline date from the store
// rather than the clock.
const latestData = computed(() => format(timeStore.endTime, 'MMMM yyyy'))

const steps = computed(() =>
	$l.value.introSteps.map((s, i) => ({
		title: s.title.replace('{date}', latestData.value),
		body: s.body,
		icon: STEP_ICONS[i],
	})),
)
const lastStep = computed(() => steps.value.length - 1)
const onLaunchStep = computed(() => step.value === lastStep.value)

const close = () => {
	store.onboardingOpen = false
}

const launch = (mode: ViewMode) => {
	store.viewMode = mode
	close()
}

// The last step parks the app's own help and achievements buttons in these
// slots rather than drawing copies of them, so that when the intro closes the
// user watches each button travel to the corner it lives in. Their click
// handlers live in Main.vue and close the intro, so reaching for either is also
// a way out.
const helpSlot = ref<HTMLElement | null>(null)
const achievementsSlot = ref<HTMLElement | null>(null)
let unliftTimer: number | undefined

const SLOTS: Record<IntroButton, { slot: Ref<HTMLElement | null>; id: string }> =
	{
		help: { slot: helpSlot, id: 'help-button' },
		achievements: { slot: achievementsSlot, id: 'achievements-button' },
	}

const parkButtons = async () => {
	await nextTick()
	for (const key of Object.keys(SLOTS) as IntroButton[]) {
		const { slot, id } = SLOTS[key]
		const btn = document.getElementById(id)
		const target = slot.value?.getBoundingClientRect()
		if (!btn || !target) continue
		// offsetLeft/offsetTop are layout values, so they give the button's resting
		// place even while it is mid-transform. getBoundingClientRect would not.
		const parent = btn.offsetParent as HTMLElement | null
		const origin = parent?.getBoundingClientRect()
		const homeX = (origin?.left ?? 0) + btn.offsetLeft + btn.offsetWidth / 2
		const homeY = (origin?.top ?? 0) + btn.offsetTop + btn.offsetHeight / 2
		store.introButtonOffsets[key] = {
			x: target.left + target.width / 2 - homeX,
			y: target.top + target.height / 2 - homeY,
		}
	}
}

// Clearing the offsets sends the buttons home under their own transitions. They
// only need to stay above the overlay for that if the overlay is on its way
// out; stepping backwards through the intro can drop them behind the glass at
// once.
const releaseButtons = (fly: boolean) => {
	clearTimeout(unliftTimer)
	store.introButtonOffsets = { help: null, achievements: null }
	if (!fly) {
		store.introButtonsLifted = false
		return
	}
	unliftTimer = window.setTimeout(() => {
		store.introButtonsLifted = false
	}, 900)
}

const next = () => {
	if (step.value < lastStep.value) step.value++
}
const back = () => {
	if (step.value > 0) step.value--
}

// Anything the user can actually operate; used to keep the box-wide "next"
// shortcuts from firing on top of a control's own behaviour.
const isControl = (target: EventTarget | null) =>
	!!(target as HTMLElement | null)?.closest('button, a, input, select')

// The whole box advances, so a click anywhere gets a response rather than
// feeling dead. The launch step has no next, where next() is a no-op.
const onBoxClick = (e: MouseEvent) => {
	if (isControl(e.target)) return
	next()
}

// Replaying from the menu re-opens the same component, so reset here rather
// than at each of the call sites that can trigger it.
watch(
	() => store.onboardingOpen,
	(open) => {
		if (open) step.value = 0
	},
)

watch([() => store.onboardingOpen, onLaunchStep], ([open, atLaunch]) => {
	if (open && atLaunch) {
		clearTimeout(unliftTimer)
		store.introButtonsLifted = true
		parkButtons()
	} else {
		releaseButtons(!open)
	}
})

const onResize = () => {
	if (store.introButtonOffsets.help) parkButtons()
}

const HANDLED_KEYS = new Set(['Escape', 'ArrowLeft', 'ArrowRight', ' ', 'Enter'])

const onKeydown = (e: KeyboardEvent) => {
	if (!store.onboardingOpen) return
	const key = e.key
	if (!HANDLED_KEYS.has(key)) return
	// Space and enter belong to whichever control has focus, if any.
	if ((key === ' ' || key === 'Enter') && isControl(e.target)) return
	e.stopPropagation()
	e.preventDefault()
	if (key === 'Escape') close()
	else if (key === 'ArrowLeft') back()
	else next()
}
// Captured on document, so these keys never reach the app's own global
// shortcuts underneath: space is play/pause on the time reel, and the arrows
// step the date.
document.addEventListener('keydown', onKeydown, true)
window.addEventListener('resize', onResize)
onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true)
	window.removeEventListener('resize', onResize)
	releaseButtons(false)
})
</script>

<template>
	<Teleport to="body">
		<Transition name="intro-fade">
			<div v-if="store.onboardingOpen" class="intro-overlay">
				<div
					class="intro-box panel glassy"
					:class="{ advances: !onLaunchStep }"
					role="dialog"
					aria-modal="true"
					:aria-label="steps[step].title"
					@click="onBoxClick"
				>
					<button
						class="intro-close glassy color"
						:aria-label="$l.introSkip"
						v-tooltip="$l.introSkip"
						@click="close"
					>
						<IconX :size="20" aria-hidden="true" />
					</button>

					<!-- The box is a fixed size, so this fills whatever the current
						step does not use and keeps the nav pinned to the bottom. -->
					<div class="intro-stage">
						<div class="intro-body">
							<component
								:is="steps[step].icon"
								class="intro-icon"
								:size="56"
								aria-hidden="true"
							/>
							<h1>{{ steps[step].title }}</h1>
							<p>{{ steps[step].body }}</p>

							<div v-if="onLaunchStep" class="intro-launch">
								<div class="event-types">
									<span class="event-types-label">
										{{ $l.introChooseEventType }}
									</span>
									<div class="event-type-buttons">
										<button
											v-for="type in EVENT_TYPES"
											:key="type.id"
											class="event-type"
											:class="[
												type.id,
												{ selected: eventStore.eventTypeMode === type.id },
											]"
											:aria-pressed="eventStore.eventTypeMode === type.id"
											@click="eventStore.setEventTypeMode(type.id)"
										>
											<component
												:is="type.icon"
												:size="22"
												aria-hidden="true"
											/>
											{{ $l.eventTypeNames[type.id] }}
										</button>
									</div>
								</div>

								<div class="mode-choices">
									<button
										class="mode-choice glassy color"
										@click="launch('timemachine')"
									>
										<IconCalendarTime :size="36" aria-hidden="true" />
										<span class="mode-name">{{ $l.introTimeMachine }}</span>
										<span class="mode-blurb">
											{{ $l.introTimeMachineBlurb }}
										</span>
									</button>
									<button
										class="mode-choice glassy color"
										@click="launch('heatmap')"
									>
										<IconEyePin :size="36" aria-hidden="true" />
										<span class="mode-name">{{ $l.introOverview }}</span>
										<span class="mode-blurb">{{ $l.introOverviewBlurb }}</span>
									</button>
								</div>

								<!-- The app's own buttons park in these slots and then
									travel to their corners when the intro closes, so their
									homes are learned rather than described. -->
								<div class="button-notes">
									<div class="button-note">
										<div
											ref="helpSlot"
											class="button-slot"
											aria-hidden="true"
										/>
										<p>{{ $l.introHelpNote }}</p>
									</div>
									<div class="button-note">
										<div
											ref="achievementsSlot"
											class="button-slot"
											aria-hidden="true"
										/>
										<p>{{ $l.introAchievementsNote }}</p>
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="intro-nav">
						<button
							class="nav-arrow glassy"
							:disabled="step === 0"
							:aria-label="$l.introBack"
							v-tooltip="$l.introBack"
							@click="back"
						>
							<IconChevronLeft :size="20" aria-hidden="true" />
						</button>

						<div class="intro-dots">
							<button
								v-for="(s, i) in steps"
								:key="s.title"
								class="intro-dot"
								:class="{ active: i === step }"
								:aria-label="`${$l.introGoToStep} ${i + 1}`"
								:aria-current="i === step"
								@click="step = i"
							/>
						</div>

						<button
							class="nav-arrow glassy"
							:disabled="onLaunchStep"
							:aria-label="$l.introNext"
							v-tooltip="$l.introNext"
							@click="next"
						>
							<IconChevronRight :size="20" aria-hidden="true" />
						</button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.intro-overlay {
	position: fixed;
	inset: 0;
	// Above the loading overlay (9999), below the help popup, which the last
	// step can open over the top of this.
	z-index: 10000;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: $panelMargin;
	background: rgba(0, 0, 0, 0.35);
	backdrop-filter: blur(6px);
}

.intro-box {
	position: relative;
	// Opaque rather than the usual translucent panel: this covers the middle of
	// a busy app, and anything showing through (the loading overlay especially)
	// competes with the text.
	background: var(--panel-surface);
	// Fixed, not fitted: sized for the launch step, which is the tallest, so
	// stepping through never resizes or reflows the box.
	width: min(94vw, 640px);
	height: min(92vh, 690px);
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: $panelMargin;
	border-radius: 2 * $borderRadius;
	box-shadow: var(--shadow-md);
	overflow: hidden;

	// Every step but the last advances on a click anywhere in the box.
	&.advances {
		cursor: pointer;
	}
}

.intro-close {
	position: absolute;
	top: 0.5rem;
	right: 0.5rem;
	width: 2.5rem;
	height: 2.5rem;
	padding: 0.5rem;
	border-radius: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: var(--shadow-sm), var(--shadow-md);

	:deep(svg) {
		flex: 0 0 auto;
	}
}

.intro-stage {
	flex: 1 1 auto;
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
	min-height: 0;
	padding: 1.5rem 0 0.5rem;
	overflow-y: auto;
}

.intro-body {
	display: flex;
	flex-direction: column;
	align-items: center;
	text-align: center;
	gap: 0.75rem;
	width: 100%;

	.intro-icon {
		color: var(--primary-glass-dark);
		flex: 0 0 auto;
	}

	h1 {
		margin: 0;
		font-size: clamp(1.3rem, 3.5vw, 1.75rem);
	}

	p {
		margin: 0;
		font-size: 1rem;
		max-width: 46ch;
		color: var(--text-secondary);
	}
}

.intro-launch {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 1rem;
	width: 100%;
	margin-top: 0.25rem;
}

.event-types {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0.4rem;

	.event-types-label {
		font-size: 0.85rem;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
}

.event-type-buttons {
	display: flex;
	gap: 0.5rem;
	flex-wrap: wrap;
	justify-content: center;
}

.event-type {
	display: flex;
	align-items: center;
	gap: 0.35rem;
	padding: 0.4rem 0.9rem;
	border-radius: $borderRadius;
	border: 1px solid var(--divider);
	background: none;
	color: inherit;
	font-size: 0.95rem;
	cursor: pointer;
	transition: all $transition;

	:deep(svg) {
		flex: 0 0 auto;
	}

	&:hover {
		background: var(--hover-bg, rgba(0, 0, 0, 0.06));
	}

	// Tinted per type so the choice reads at a glance, the same way the wheel
	// in the menu is coloured.
	&.selected {
		color: var(--panel-surface);
		border-color: transparent;

		&.hot {
			background: var(--theme-hot-primary-glass);
		}
		&.cold {
			background: var(--theme-cold-primary-glass);
		}
		&.wet {
			background: var(--theme-wet-primary-glass);
		}
	}
}

.mode-choices {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
	justify-content: center;
	width: 100%;
}

.mode-choice {
	flex: 0 1 13rem;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0.3rem;
	padding: 1rem 0.75rem;
	border-radius: 2 * $borderRadius;

	:deep(svg) {
		flex: 0 0 auto;
	}

	.mode-name {
		font-size: 1.15rem;
		font-weight: 600;
	}

	.mode-blurb {
		font-size: 0.85rem;
		opacity: 0.85;
		line-height: 1.3;
	}
}

.button-notes {
	display: flex;
	flex-direction: column;
	gap: 0.6rem;
	max-width: 46ch;
}

.button-note {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	text-align: left;

	// Reserves exactly the footprint of the real button so the layout does not
	// shift when it is parked over the top of the slot.
	.button-slot {
		flex: 0 0 auto;
		width: 2.5rem;
		height: 2.5rem;
	}

	p {
		margin: 0;
		font-size: 0.85rem;
		color: var(--text-secondary);
	}
}

.intro-nav {
	flex: 0 0 auto;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 1.5rem;
	padding-bottom: 0.5rem;

	.nav-arrow {
		flex: 0 0 auto;
		width: 2.25rem;
		height: 2.25rem;
		padding: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 100%;

		:deep(svg) {
			flex: 0 0 auto;
		}

		&:disabled {
			opacity: 0.3;
			cursor: default;
		}
	}
}

.intro-dots {
	display: flex;
	align-items: center;
	gap: 0.45rem;

	.intro-dot {
		width: 0.55rem;
		height: 0.55rem;
		padding: 0;
		border: none;
		border-radius: 100%;
		background: var(--text-tertiary);
		opacity: 0.35;
		cursor: pointer;
		transition: all $transition;

		&.active {
			opacity: 1;
			background: var(--primary-glass-dark);
			transform: scale(1.3);
		}
	}
}

.intro-fade-enter-active,
.intro-fade-leave-active {
	transition: opacity $transition;

	.intro-box {
		transition: transform $transition;
	}
}
.intro-fade-enter-from,
.intro-fade-leave-to {
	opacity: 0;

	.intro-box {
		transform: scale(0.95);
	}
}
</style>
