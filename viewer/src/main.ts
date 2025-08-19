import App from '@/App.vue'
import '@/assets/styles/main.scss'
import { createI18n, useLabels } from '@/lib/labels'
import router from '@/router'
import { useStore } from '@/store/store'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

const store = useStore()
// TODO use language store here (if required)
const i18n = createI18n(() => store.lang)
app.use(i18n)

{
	;(globalThis as any).$l = useLabels()
}

app.mount('#app')
