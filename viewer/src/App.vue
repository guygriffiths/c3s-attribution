<script setup lang="ts">
import { onMounted } from 'vue'
import 'vue3-loading-overlay/dist/vue3-loading-overlay.css'
import Loading from 'vue3-loading-overlay'
import AppHeader from '@/components/common/AppHeader.vue'
import AppFooter from '@/components/common/Footer.vue'
import { useLabels } from '@/lib/labels'
import { useStore } from '@/store/store'
import { useStore as useEventStore } from '@/store/eventStore'

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
})
</script>

<template id="app">
	<loading :active="store.isLoading" :isFullPage="true" id="loading"></loading>
	<!-- <AppHeader id="header" /> -->
	<router-view id="main"></router-view>
	<!-- <AppFooter id="footer" /> -->
</template>

<style lang="scss">
@forward '@/assets/styles/main.scss';
@use '@/assets/styles/scssVars.module.scss' as *;

#app {
	width: 100vw;
	height: 100vh;
	max-width: 100vw;
	max-height: 100vh;
	// display: grid;
	// grid-template-columns: 100%;
	// grid-template-rows: $headerHeight + $gap 1fr $footerHeight + $gap;
	// grid-template-areas: 'header' 'main' 'footer';

	#loading {
		width: 100vw;
		height: 100vh;
		position: absolute;
		margin: auto;
		backdrop-filter: $frosty;
	}

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
