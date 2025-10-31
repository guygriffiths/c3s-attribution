import vue from '@vitejs/plugin-vue'
import { copyFileSync, readdirSync, statSync } from 'fs'
import path, { join } from 'path'
import { defineConfig, loadEnv } from 'vite'

const ENV_PREFIX = 'X_'

export default defineConfig(({ command, mode }) => {
	process.env = { ...process.env, ...loadEnv(mode, process.cwd(), ENV_PREFIX) }
	return {
		build: {
			outDir: './dist',
		},
		envPrefix: ENV_PREFIX,
		resolve: {
			alias: {
				'@': path.resolve(__dirname, './src'),
			},
		},
		// First option should be the final deploy point of the client
		base: command === 'build' ? process.env.X_PUBLIC_PATH : '/',
		plugins: [
			vue(),
			{
				name: 'copy-selected-public',
				writeBundle() {
					const publicDir = 'public'
					const distDir = 'dist'
					const skipDir = 'data'

					const copyRecursive = (src: string, dest: string) => {
						readdirSync(src).forEach((file) => {
							if (file === skipDir) return
							const srcPath = join(src, file)
							const destPath = join(dest, file)
							const stats = statSync(srcPath)
							if (stats.isDirectory()) {
								copyRecursive(srcPath, destPath)
							} else {
								copyFileSync(srcPath, destPath)
							}
						})
					}
					copyRecursive(publicDir, distDir)
				},
			},
		],
		css: {
			preprocessorOptions: {
				scss: {},
			},
		},
	}
})
