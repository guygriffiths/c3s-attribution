<script setup lang="ts">
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { useLabels } from '@/lib/labels'

const store = useStore()
const eventStore = useEventStore()
const $l = useLabels()
const getLabelForEventType = (type: SelectedEventType) => {
	if (type === 'hot') return $l.value.hotTitle
	if (type === 'cold') return $l.value.coldTitle
	if (type === 'wet') return $l.value.wetTitle
	if (type === 'hotcold') return $l.value.hotcoldTitle
	if (type === 'hotwet') return $l.value.hotwetTitle
	if (type === 'coldwet') return $l.value.coldwetTitle
	return type
}
</script>
<template>
	<div
		class="app-logo"
		:class="{ 'disable-pointer-events': store.isFocused }"
		:aria-label="
			'Extreme ' + getLabelForEventType(eventStore.eventTypeMode) + ' Explorer'
		"
	>
		<div class="title-wrapper" :class="{ square: store.mainHelpOpen }">
			<img src="@/assets/img/c3s-logo.png" alt="C3S Logo" aria-hidden="true" />
			<h1 aria-hidden="true">
				{{ $l.title }} -
				<span class="eventtype" role="button" tabindex="-1">
					{{ getLabelForEventType(eventStore.eventTypeMode) }}
				</span>
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
		width: 100%;

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

		h1 {
			// font-size: $headerHeight * 0.6;
			margin: 0;
			white-space: nowrap;
			line-height: 1;
			font-size: clamp(1.5rem, 2vw, $headerHeight * 0.8);
		}

		.eventtype {
			color: var(--primary);
			cursor: pointer;
			pointer-events: auto;
		}
	}
}
</style>
