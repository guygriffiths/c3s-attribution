/// <reference types="vite/client" />

declare module '*.vue' {
	import { DefineComponent } from 'vue'
	// eslint-disable-next-line
	const component: DefineComponent<{}, {}, any>
	export default component
}


declare module '*.module.scss' {
  const content: { [key: string]: string }
  export default content
  export const c3sred: string
  export const c3sblue: string
  export const c3spurple: string
  export const c3sgreen: string
  export const c3sorange: string
  export const c3sgrey: string
  export const lightbulb: string
  export const animTime: string
  export const frameBorderWidth: string
  export const panelMargin: string
}
