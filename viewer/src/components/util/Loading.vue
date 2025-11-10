<script setup lang="ts">
defineProps({
	message: {
		type: String,
		default: 'Loading...',
	},
	progress: {
		type: Number,
		default: null,
	},
	showProgress: {
		type: Boolean,
		default: false,
	},
	id: {
		type: String,
		default: 'loading-overlay',
	},
})
</script>

<template>
	<Teleport to="body">
		<div class="loading-content" :id="id">
			<!-- Dual spinner -->
			<div class="spinner-container">
				<div class="spinner-ring"></div>
				<div class="spinner-ring-inner"></div>
			</div>

			<!-- Message -->
			<p class="loading-message">Please wait...</p>
			<p class="loading-subtitle">{{ message }}</p>

			<!-- Optional progress -->
			<div v-if="showProgress && progress !== null" class="progress-container">
				<div class="progress-bar">
					<div class="progress-fill" :style="{ width: progress + '%' }"></div>
				</div>
				<p class="progress-text">{{ Math.round(progress) }}%</p>
			</div>
		</div>
	</Teleport>
</template>

<style scoped lang="scss">
@use '@/assets/styles/scssVars.module.scss' as *;

.loading-overlay {
}

.loading-content {
	inset: 0;
	z-index: 9999;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	cursor: wait;
	padding: 2rem 2.5rem;
	border-radius: 1rem;
	background: var(--panel-solid);
	backdrop-filter: $frosty;
	border-radius: 0;
}

.spinner-container {
	position: relative;
	width: 64px;
	height: 64px;
	margin: 0 auto 1.5rem;
}

.spinner-ring {
	position: absolute;
	inset: 0;
	border: 4px solid var(--text-on-primary);
	border-radius: 50%;
}

.spinner-ring::after {
	content: '';
	position: absolute;
	inset: 0;
	border: 4px solid transparent;
	border-top-color: rgba($c3sred, 0.5);
	border-radius: 50%;
	animation: spin 1s linear infinite;
}

.spinner-ring-inner {
	position: absolute;
	inset: 8px;
	border: 4px solid transparent;
	border-top-color: rgba($c3sblue, 0.5);
	border-radius: 50%;
	animation: spin 1.5s linear infinite reverse;
}

@keyframes spin {
	0% {
		transform: rotate(0deg);
	}
	100% {
		transform: rotate(360deg);
	}
}

.loading-message {
	margin: 0 0 0.25rem 0;
	color: var(--text-primary);
	font-size: 1rem;
	font-weight: 500;
	animation: pulse 2s ease-in-out infinite;
}

.loading-subtitle {
	margin: 0;
	color: var(--text-secondary);
	font-size: 0.875rem;
}

@keyframes pulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.6;
	}
}

.progress-container {
	margin-top: 1.5rem;
}

.progress-bar {
	width: 240px;
	height: 6px;
	background: #e5e7eb;
	border-radius: 3px;
	overflow: hidden;
	margin: 0 auto;
}

.progress-fill {
	height: 100%;
	background: linear-gradient(
		90deg,
		var(--theme-cold-primary-glass-shine) 0%,
		var(--theme-hot-primary-glass-shine) 50%,
		var(--theme-cold-primary-glass-shine) 100%
	);
	background-size: 200% 100%;
	border-radius: 3px;
	transition: width 0.3s ease-out;
	animation: shimmer 2s linear infinite;
}

@keyframes shimmer {
	0% {
		background-position: 200% 0;
	}
	100% {
		background-position: -200% 0;
	}
}

.progress-text {
	margin: 0.5rem 0 0 0;
	color: #6b7280;
	font-size: 0.75rem;
	font-weight: 500;
}

.fade-enter-active {
	transition: opacity 0.15s ease-out;
}

.fade-leave-active {
	transition: opacity 0.2s ease-in;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}

.fade-enter-active .loading-content {
	animation: scaleIn 0.3s ease-out;
}

@keyframes scaleIn {
	0% {
		opacity: 0;
		transform: scale(0.9);
	}
	100% {
		opacity: 1;
		transform: scale(1);
	}
}
</style>
