<script setup lang="ts">
import { onMounted } from 'vue'
import 'vue3-loading-overlay/dist/vue3-loading-overlay.css'
import Loading from '@/components/util/Loading.vue'
import AppHeader from '@/components/common/AppHeader.vue'
import AppFooter from '@/components/common/Footer.vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'
import HelpOverlay from './components/util/HelpOverlay.vue'
import { helpMe } from './lib/help'

const l = useLabels()
const store = useStore()
const eventStore = useEventStore()

onMounted(() => {
	document.title = l.value.title
	eventStore.init()

	let resizeTimer: number

	window.addEventListener('resize', () => {
		document.body.classList.add('disable-transitions')

		clearTimeout(resizeTimer)
		resizeTimer = window.setTimeout(() => {
			document.body.classList.remove('disable-transitions')
		}, 200) // tweak delay as needed
	})

	helpMe('aboutInfo')
})
</script>

<template id="app">
	<loading
		id="loading-overlay"
		:message="store.loadingMessage || 'Loading...'"
		:progress="50"
		:show-progress="false"
	></loading>
	<HelpOverlay />
	<!-- <AppHeader id="header" /> -->
	<router-view id="main"></router-view>
	<!-- <AppFooter id="footer" /> -->
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

			@extend .glassy;
			@extend .color;

			box-shadow: none !important;
		}

		/* Target the span with the X */
		button.shepherd-cancel-icon span {
			display: flex !important;
			align-items: center !important;
			justify-content: center !important;
			line-height: 1 !important;
			font-size: 1.5rem !important;
			margin: 0 !important;
			padding: 0 !important;
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
	// display: grid;
	// grid-template-columns: 100%;
	// grid-template-rows: $headerHeight + $gap 1fr $footerHeight + $gap;
	// grid-template-areas: 'header' 'main' 'footer';

	#header {
		grid-area: header;
	}

	#main {
		// grid-area: main;
		// // Constrains certain badly-behaved elements
		// max-height: calc(100vh - $headerHeight - $footerHeight - 2 * $gap);
		// padding: 1rem;
		height: 100vh;
		max-height: 100vh;
		overflow: clip;
	}

	#footer {
		grid-area: footer;
	}
}
</style>
