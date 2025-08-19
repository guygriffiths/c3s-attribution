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
}
