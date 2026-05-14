<script setup lang="ts">
import { IconTrophy } from '@tabler/icons-vue'
import { closeHelp } from '@/lib/help'
</script>

<template>
	<div class="hard-mode-unlocked">
		<div class="trophy-row">
			<IconTrophy size="48" class="trophy-icon" aria-hidden="true" />
		</div>
		<p>
			You've completed all the basic achievements. A whole new set of
			advanced challenges is now waiting for you!
		</p>
		<p>
			Visit the <strong>achievements panel</strong> (the trophy button) to
			explore the hard mode challenges, grouped by section.
		</p>
		<p class="hint">
			Some may already be complete — they unlock retroactively based on
			what you've already done.
		</p>
		<button class="got-it-btn glassy color" @click="closeHelp">Got it!</button>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.hard-mode-unlocked {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	max-width: 360px;
}

.trophy-row {
	display: flex;
	justify-content: center;
	padding: 0.5rem 0;

	.trophy-icon {
		color: $lightbulb;
		filter: drop-shadow(0 0 12px rgba(247, 205, 81, 0.6));
	}
}

p {
	margin: 0;
	font-size: 0.9rem;
	line-height: 1.5;
}

.hint {
	font-size: 0.8rem;
	opacity: 0.65;
	font-style: italic;
}

.got-it-btn {
	align-self: flex-end;
	margin-top: 0.25rem;
	padding: 0.375rem 1rem;
	border-radius: 6px;
	font-size: 0.875rem;
	cursor: pointer;
}
</style>
