<script setup lang="ts">
import { IconDice, IconRainbow } from '@tabler/icons-vue'
import { closeHelp } from '@/lib/help'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
</script>

<template>
	<div class="all-complete">
		<div class="icon-row" aria-hidden="true">
			<IconRainbow size="48" class="rainbow-icon" />
		</div>
		<h3>You've mastered {{ $l.title }}!</h3>
		<p>
			Every achievement is complete. You've explored the full depth of this
			tool — congratulations!
		</p>
		<p>
			As a reward, a <strong>random event</strong> button
			(<IconDice :size="16" style="vertical-align: middle;" aria-hidden="true" />)
			has appeared in the top bar. Hit it any time to jump to a surprise
			event from across all time.
		</p>
		<button class="got-it-btn glassy color" @click="closeHelp">
			Let's go!
		</button>
	</div>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.all-complete {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	max-width: 360px;
}

.icon-row {
	display: flex;
	justify-content: center;
	padding: 0.5rem 0;

	.rainbow-icon {
		color: hsl(280, 70%, 55%);
		filter: drop-shadow(0 0 14px rgba(180, 100, 255, 0.5));
	}
}

h3 {
	margin: 0;
	font-size: 1.1rem;
	font-weight: 600;
}

p {
	margin: 0;
	font-size: 0.9rem;
	line-height: 1.5;
}

.got-it-btn {
	margin-top: 0.25rem;
	align-self: flex-end;
	padding: 0.375rem 1rem;
	border-radius: 6px;
	font-size: 0.875rem;
	cursor: pointer;
}
</style>
