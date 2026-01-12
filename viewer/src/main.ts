import App from '@/App.vue'
import '@/assets/styles/main.scss'
import { createI18n } from '@/lib/labels'
import router from '@/router'
import { useStore } from '@/store/store'
import FloatingVue from 'floating-vue'
import 'floating-vue/dist/style.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

app.use(FloatingVue, {
	themes: {
		'info-tooltip': {
			delay: { show: 300, hide: 0 },
		},
	},
})

// In your main.js or wherever you configure Vue
import { vTooltip } from 'floating-vue'

app.directive('tooltip', {
	beforeMount(el, binding) {
		// Extract the tooltip content
		const content =
			typeof binding.value === 'string' ? binding.value : binding.value?.content

		// Add aria-label automatically
		if (content) {
			el.setAttribute('aria-label', content)
		}

		// Call FloatingVue's original directive
		vTooltip.beforeMount(el, binding)
	},

	updated(el, binding) {
		// Update aria-label if content changes
		const content =
			typeof binding.value === 'string' ? binding.value : binding.value?.content

		if (content) {
			el.setAttribute('aria-label', content)
		}

		// Call FloatingVue's update hook
		if (vTooltip.updated) {
			vTooltip.updated(el, binding)
		}
	},

	beforeUnmount(el) {
		// Call FloatingVue's cleanup
		if (vTooltip.beforeUnmount) {
			vTooltip.beforeUnmount(el)
		}
	},
})

const store = useStore()
// TODO use language store here (if required)
const i18n = createI18n(() => store.lang)
app.use(i18n)

app.mount('#app')
