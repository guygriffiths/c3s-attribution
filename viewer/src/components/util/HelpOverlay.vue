<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { activeHelp, closeHelp } from '@/lib/help'
import { computePosition, flip, shift, offset } from '@floating-ui/dom'
import { IconHelp, IconX } from '@tabler/icons-vue'

const popupEl = ref<HTMLElement | null>(null)
const popupStyle = ref({ left: '0px', top: '0px' })

// Extract positioning logic
const updatePosition = async () => {
	if (!activeHelp.value || !popupEl.value) return

	const targetEl: HTMLElement | null = activeHelp.value.target
		? document.querySelector(activeHelp.value.target)
		: null

	if (!targetEl) {
		// Center on screen
		const vw = Math.max(
			document.documentElement.clientWidth || 0,
			window.innerWidth || 0,
		)
		const vh = Math.max(
			document.documentElement.clientHeight || 0,
			window.innerHeight || 0,
		)
		const popupRect = popupEl.value.getBoundingClientRect()
		const left = (vw - popupRect.width) / 2
		const top = (vh - popupRect.height) / 2
		popupStyle.value = { left: `${left}px`, top: `${top}px` }
		return
	}
	const { x, y } = await computePosition(targetEl, popupEl.value, {
		placement: activeHelp.value.on || 'bottom',
		middleware: [offset(12), flip(), shift({ padding: 8 })],
	})

	popupStyle.value = { left: `${x}px`, top: `${y}px` }
}

watch(
	activeHelp,
	async (help) => {
		if (!help || !popupEl.value) return

		const targetEls: NodeListOf<HTMLElement> | null = help.target
			? document.querySelectorAll(help.target)
			: null
			console.log('help targetEls', targetEls)
		if (!targetEls || targetEls.length === 0) {
			// console.warn(`No target element found for selector: ${help.target}`)
			// return
		} else {
			targetEls.forEach(el => el.classList.add('help-highlighted'))
		}
		requestAnimationFrame(() => {
			requestAnimationFrame(() => {
				updatePosition()
			})
		})
	},
	{ flush: 'post' },
)

const handleClose = () => {
	const targetEls: NodeListOf<HTMLElement> | null = activeHelp.value?.target
		? document.querySelectorAll(activeHelp.value?.target)
		: null
	if (targetEls) {
		targetEls.forEach(el => el.classList.remove('help-highlighted'))
	}
	closeHelp()
}

// Reposition after content loads
const onContentLoaded = () => {
	requestAnimationFrame(() => {
		updatePosition()
	})
}

// Add resize listener to update position, using modern JS API
if (typeof ResizeObserver !== 'undefined') {
	const resizeObserver = new ResizeObserver(() => {
		updatePosition()
	})
	resizeObserver.observe(document.body)
} else {
	// Fallback for browsers without ResizeObserver
	window.addEventListener('resize', () => {
		updatePosition()
	})
}
</script>

<template>
	<Teleport to="body">
		<div v-if="activeHelp" class="help-overlay">
			<div class="help-backdrop" @click="handleClose"></div>

			<div ref="popupEl" class="help-popup glassy panel" :style="popupStyle">
				<button class="help-close glassy color flat" @click="handleClose">
					<IconX aria-hidden="true" />
				</button>
				<div class="title-wrapper">
					<IconHelp size="32" aria-hidden="true" />
					<h1>{{ activeHelp.title }}</h1>
				</div>

				<Suspense @resolve="onContentLoaded">
					<component :is="activeHelp.component" />
					<template #fallback>
						<div class="help-loading">Loading...</div>
					</template>
				</Suspense>
			</div>
		</div>
	</Teleport>
</template>

<style scoped>
/* ... existing styles ... */

.help-loading {
	min-height: 100px; /* Give it some space while loading */
	display: flex;
	align-items: center;
	justify-content: center;
}
</style>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.help-backdrop {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.2);
	backdrop-filter: $frosty;
	z-index: 9998;
	overflow: hidden;
}

.help-popup {
	position: fixed;
	z-index: 10000;
	max-width: min(90vw, 640px);

	max-height: 80vh;
	padding: $panelMargin;
	border-radius: 8px;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
	display: flex;
	flex-direction: column;
	justify-content: stretch;

	.title-wrapper {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		color: var(--primary);
		margin-bottom: 0.5rem;
		h1 {
			margin: 0 2rem 0 0;
			padding: 0;
			font-size: 1.5rem;
			flex: 1 1 100%;
		}

		svg {
			margin-right: auto;
		}
	}
}

.help-close {
	position: absolute;
	top: 0;
	right: 0;
	border-top-left-radius: 0;
	border-bottom-right-radius: 0;
	background: none;
	border: none;
	font-size: 1.5rem;
	cursor: pointer;
	padding: 0;
	width: 1.5rem;
	height: 1.5rem;
	display: flex;
	align-items: center;
	justify-content: center;
	line-height: 1;
	opacity: 0.7;
	transition: opacity 0.2s;
}

.help-close:hover {
	opacity: 1;
}

:global(.help-highlighted) {
	position: relative;
	z-index: 9999 !important;
	box-shadow: 0 0 1rem $lightbulb;
	pointer-events: none;
}
</style>

<style>
.help-content {
	overflow-y: auto;
	background: var(--panel-bg);
}
</style>
