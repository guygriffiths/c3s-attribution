<script setup lang="ts">
import { onMounted } from 'vue'
import 'vue3-loading-overlay/dist/vue3-loading-overlay.css'
import Loading from '@/components/util/Loading.vue'
import HelpOverlay from '@/components/util/HelpOverlay.vue'
import OnboardingIntro from '@/components/OnboardingIntro.vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import { usePersistentStore } from '@/store/persistentStore'
import { useUserRegionsStore } from '@/store/userRegionsStore'

const l = useLabels()
const store = useStore()
const eventStore = useEventStore()
const persistentStore = usePersistentStore()
const userRegionsStore = useUserRegionsStore()

onMounted(() => {
	// Set page title from labels
	document.title = l.value.title
	
	// Initialize event store
	eventStore.init()

	// Load user-uploaded regions from localStorage
	userRegionsStore.loadFromStorage()
	
	// Disable transitions during resize to prevent janky animations
	let resizeTimer: number
	window.addEventListener('resize', () => {
		document.body.classList.add('disable-transitions')
		clearTimeout(resizeTimer)
		resizeTimer = window.setTimeout(() => {
			document.body.classList.remove('disable-transitions')
		}, 500)
	})
	
	// Show the intro on the first visit only — after that it is on demand, from
	// "Replay introduction" in the menu. The About panel is no longer part of
	// startup; it opens only from the info button.
	if (!persistentStore.introSeen) {
		store.onboardingOpen = true
		persistentStore.setIntroSeen()
	}
})
</script>

<template>
	<Loading
		id="loading-overlay"
		:message="store.loadingMessage || 'Loading...'"
		:progress="50"
		:show-progress="false"
	/>
	
	<HelpOverlay />
	
	<OnboardingIntro />
	
	<router-view id="main" />
	
	<!-- SVG filters for Shepherd tour effects -->
	<svg width="0" height="0">
		<defs>
			<filter id="shepherd-blur">
				<feGaussianBlur in="SourceGraphic" stdDeviation="8" />
			</filter>
		</defs>
	</svg>
</template>

<style lang="scss">
@forward '@/assets/styles/main.scss';
@use '@/assets/styles/scssVars.module.scss' as *;

.shepherd-element {
	margin: -12px !important;
	background: var(--panel-bg) !important;
}

.shepherd-content {
	background: var(--panel-bg) !important;
	
	.shepherd-header {
		background-color: rgba(0, 0, 0, 0.1) !important;
		display: flex !important;
		align-items: center !important;
		
		button.shepherd-cancel-icon {
			padding: 0 !important;
			margin: 0 !important;
			width: 2rem !important;
			height: 2rem !important;
			display: flex !important;
			align-items: center !important;
			justify-content: center !important;
			line-height: 1 !important;
			color: var(--text-on-primary) !important;
			box-shadow: none !important;
			@extend .glassy;
			@extend .color;
			
			span {
				display: flex !important;
				align-items: center !important;
				justify-content: center !important;
				line-height: 1 !important;
				font-size: 1.5rem !important;
				margin: 0 !important;
				padding: 0 !important;
			}
		}
	}
	
	.shepherd-text {
		background: var(--panel-bg) !important;
	}
}

#loading-overlay {
	position: fixed;
	width: 100vw;
	height: 100vh;
	top: 0;
	left: 0;
	margin: 0;
}

#app {
	width: 100vw;
	height: 100vh;
	max-width: 100vw;
	max-height: 100vh;
	
	#header {
		grid-area: header;
	}
	
	#main {
		height: 100vh;
		max-height: 100vh;
		overflow: clip;
	}
	
	#footer {
		grid-area: footer;
	}
}
</style>