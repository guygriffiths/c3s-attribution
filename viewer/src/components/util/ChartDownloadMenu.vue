<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { IconDownload, IconTable, IconPhoto } from '@tabler/icons-vue'

const emit = defineEmits<{
	csv: []
	image: []
}>()

const props = defineProps<{
	disabled?: boolean
}>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)

function toggle() {
	if (props.disabled) return
	open.value = !open.value
}
function choose(what: 'csv' | 'image') {
	open.value = false
	if (what === 'csv') emit('csv')
	else emit('image')
}
function onDocClick(e: MouseEvent) {
	if (rootRef.value && !rootRef.value.contains(e.target as Node)) {
		open.value = false
	}
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
	<div ref="rootRef" class="download-menu">
		<button
			class="download-btn"
			@click.stop="toggle"
			v-tooltip="'Download chart'"
			aria-label="Download chart"
			:aria-expanded="open"
			:disabled="disabled"
		>
			<IconDownload :size="14" />
		</button>
		<div v-if="open" class="download-popover">
			<button class="popover-item" @click.stop="choose('csv')">
				<IconTable :size="14" />
				<span>Data (CSV)</span>
			</button>
			<button class="popover-item" @click.stop="choose('image')">
				<IconPhoto :size="14" />
				<span>Image (PNG)</span>
			</button>
		</div>
	</div>
</template>

<style scoped lang="scss">
.download-menu {
	position: absolute;
	top: 0;
	left: 0;
	z-index: 20;

	.download-btn {
		background: var(--panel-bg-night);
		border: 1px solid var(--divider);
		border-radius: 0;
		border-bottom-right-radius: 4px;
		padding: 2px 4px;
		cursor: pointer;
		opacity: 0.5;
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		transition: opacity 0.15s;
		&:hover {
			opacity: 1;
		}
		&:disabled {
			cursor: default;
			opacity: 0.3;
		}
		svg {
			pointer-events: none;
			width: 14px;
			height: 14px;
			color: inherit;
		}
	}

	.download-popover {
		position: absolute;
		top: 100%;
		left: 0;
		margin-top: 2px;
		display: flex;
		flex-direction: column;
		background: var(--panel-bg-night);
		border: 1px solid var(--divider);
		border-radius: 4px;
		box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.3);
		overflow: hidden;

		.popover-item {
			display: flex;
			align-items: center;
			gap: 0.4rem;
			padding: 0.3rem 0.6rem 0.3rem 0.4rem;
			background: transparent;
			border: none;
			cursor: pointer;
			color: var(--text-secondary);
			font-size: 0.75rem;
			white-space: nowrap;
			transition: background 0.15s;
			&:hover {
				background: var(--divider);
				color: var(--text-primary);
			}
			svg {
				pointer-events: none;
				flex: 0 0 auto;
			}
		}
	}
}
</style>
