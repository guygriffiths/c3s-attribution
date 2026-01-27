<script setup lang="ts">
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useLabels } from '@/lib/labels'

const store = useStore()
const eventStore = useEventStore()
const $l = useLabels()
</script>
<template>
	<div
		class="app-logo"
		:class="{ 'disable-pointer-events': store.isFocused }"
		:aria-label="
			eventStore.eventTypeMode === 'hot'
				? $l.hotTitle
				: eventStore.eventTypeMode === 'cold'
					? $l.coldTitle
					: $l.hotcoldTitle
		"
	>
		<div class="title-wrapper" :class="{ square: store.mainHelpOpen }">
			<img src="@/assets/img/c3s-logo.png" alt="C3S Logo" aria-hidden="true" />
			<h1 aria-hidden="true">
				Extreme
				<span
					class="eventtype"
					@click="eventStore.cycleEventType()"
					role="button"
					tabindex="-1"
				>
					{{
						eventStore.eventTypeMode === 'hot'
							? 'Heat Event'
							: eventStore.eventTypeMode === 'cold'
								? 'Cold Event'
								: 'Event'
					}}
				</span>
				Explorer
			</h1>
		</div>
	</div>
</template>
<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.app-logo {
	pointer-events: none;
	display: flex;
	flex-direction: column;
	gap: 0;
	align-items: flex-start;

	button.expand {
		position: absolute;
		bottom: 0;
		right: 0;
		padding: 0;
		transform: translate(50%, 50%);
		display: flex;
		pointer-events: all;
		transition: all $animTime $animEase $animTime;
		z-index: 10;

		&.disabled {
			transition: all 0 $animEase;
			opacity: 0;
			pointer-events: none;
		}

		&.close {
			bottom: unset;
			top: 0;
			transform: translate(0, 0);
			border-radius: $borderRadius;
			border-top-left-radius: 0;
			border-bottom-right-radius: 0;
			box-shadow: none;
		}

		svg {
			margin: 0;
		}
	}

	.title-wrapper {
		z-index: 5;
		background: var(--panel-bg);
		border-radius: $borderRadius;
		box-shadow: var(--shadow-md);
		backdrop-filter: $frosty;
		padding: 0.25rem 0.5rem;
		display: flex;
		align-items: center;
		height: $headerHeight;
		transition: all $animTime $animEase $animTime;

		&.square {
			transition: all 0s $animEase;
			border-bottom-left-radius: 0;
			border-bottom-right-radius: 0;
			box-shadow: none;
		}

		img {
			height: 100%;
			width: auto;
			margin-right: 0.5rem;
		}

		.eventtype {
			color: var(--primary);
			cursor: pointer;
			pointer-events: auto;
		}
	}
}
</style>
