<script setup lang="ts">
import { ref, computed } from 'vue'
import {
	IconCloudRain,
	IconTemperatureSnow,
	IconTemperatureSun,
	IconSun,
	IconSnowflake,
} from '@tabler/icons-vue'
import type { Component } from 'vue'
import { useStore as useEventStore } from '@/store/eventStore'
import { useLabels } from '@/lib/labels'

const $l = useLabels()
const eventStore = useEventStore()
const model = defineModel<SelectedEventType>()

const hoveredId = ref<SelectedEventType | null>(null)

// ── Ring geometry ────────────────────────────────────────────────────────────
// SVG viewBox 0 0 200 200, angles measured clockwise from east (3 o'clock).
// 10 o'clock = 210°, 2 o'clock = 330°, 6 o'clock = 90°.
//
// Span sizes: single types (hot/cold/wet) = 72°, combos = 48°.
// 3×72 + 3×48 = 360° — full ring, no overlap.
//
// Segment order (clockwise from hot):
//   hot [174–246]  hotcold [246–294]  cold [294–366]
//   coldwet [6–54] wet [54–126]       hotwet [126–174]
const CX = 100,
	CY = 100
const OR = 88,
	IR = 30 // outer / inner radii
const MR = (OR + IR) / 2 // mid-ring radius = 70
const GAP = 0.5 // degrees of gap between segments

function rad(d: number) {
	return (d * Math.PI) / 180
}

function pt(r: number, deg: number): [number, number] {
	return [CX + r * Math.cos(rad(deg)), CY + r * Math.sin(rad(deg))]
}

function arcPath(a0: number, a1: number): string {
	const end = a1 <= a0 ? a1 + 360 : a1
	const s = a0 + GAP,
		e = end - GAP
	const span = e - s
	const [ox0, oy0] = pt(OR, s),
		[ox1, oy1] = pt(OR, e)
	const [ix1, iy1] = pt(IR, e),
		[ix0, iy0] = pt(IR, s)
	const la = span > 180 ? 1 : 0
	const f = (n: number) => n.toFixed(2)
	return (
		`M${f(ox0)},${f(oy0)} A${OR},${OR} 0 ${la} 1 ${f(ox1)},${f(oy1)} ` +
		`L${f(ix1)},${f(iy1)} A${IR},${IR} 0 ${la} 0 ${f(ix0)},${f(iy0)} Z`
	)
}

type LabelKey = keyof ReturnType<typeof useLabels>['value']

interface SegBase {
	id: SelectedEventType
	a0: number
	a1: number
	ac: number
	icons: Component[]
	tooltipKey: LabelKey
}

const SEG_DEFS: SegBase[] = [
	{
		id: 'hot',
		a0: 174,
		a1: 246,
		ac: 210,
		icons: [IconTemperatureSun],
		tooltipKey: 'selectHeatwaveEvents',
	},
	{
		id: 'hotcold',
		a0: 246,
		a1: 294,
		ac: 270,
		icons: [IconSun, IconSnowflake],
		tooltipKey: 'selectAllTemperatureEvents',
	},
	{
		id: 'cold',
		a0: 294,
		a1: 366,
		ac: 330,
		icons: [IconTemperatureSnow],
		tooltipKey: 'selectColdwaveEvents',
	},
	{
		id: 'coldwet',
		a0: 6,
		a1: 54,
		ac: 30,
		icons: [IconCloudRain, IconSnowflake],
		tooltipKey: 'selectColdWetEvents',
	},
	{
		id: 'wet',
		a0: 54,
		a1: 126,
		ac: 90,
		icons: [IconCloudRain],
		tooltipKey: 'selectWetwaveEvents',
	},
	{
		id: 'hotwet',
		a0: 126,
		a1: 174,
		ac: 150,
		icons: [IconSun, IconCloudRain],
		tooltipKey: 'selectHotWetEvents',
	},
]

const segments = computed(() => {
	const l = $l.value
	return SEG_DEFS.map((s) => {
		const [cx, cy] = pt(MR, s.ac)
		return {
			...s,
			path: arcPath(s.a0, s.a1),
			cx,
			cy,
			combined: s.icons.length > 1,
			tooltip: String(l[s.tooltipKey]),
		}
	})
})

// Convert SVG coordinate to CSS percentage within the 200×200 viewBox
function pct(v: number) {
	return `${(v / 200) * 100}%`
}

async function select(id: SelectedEventType) {
	model.value = id
	await eventStore.setEventTypeMode(id)
}
</script>

<template>
	<div class="ring-container">
		<!-- Visual ring — pointer-events disabled; hover driven by JS -->
		<svg viewBox="0 0 200 200" class="ring-svg" aria-hidden="true">
			<defs>
				<!--
					All gradients use userSpaceOnUse so directions are exact.
					Ring center (100,100), MR=64. Tangent direction at angle θ = (−sinθ, cosθ).

					hotcold (ac=270°): tangent = (1,0) → purely horizontal.
					  hot end at 246° is upper-left, cold end at 294° is upper-right.
					  y=36 is the arc midpoint height.
				-->
				<linearGradient id="grad-hotcold" gradientUnits="userSpaceOnUse" x1="40" y1="36" x2="160" y2="36">
					<stop offset="0%" class="stop-hot" />
					<stop offset="100%" class="stop-cold" />
				</linearGradient>
				<!--
					coldwet (ac=30°): tangent = (−sin30°, cos30°) = (−0.5, 0.866).
					  cold end at 6° → (185, 80),  wet end at 54° → (125, 184).
				-->
				<linearGradient id="grad-coldwet" gradientUnits="userSpaceOnUse" x1="185" y1="80" x2="125" y2="184">
					<stop offset="0%" class="stop-cold" />
					<stop offset="100%" class="stop-wet" />
				</linearGradient>
				<!--
					hotwet (ac=150°): tangent = (−sin150°, cos150°) = (−0.5, −0.866).
					  wet end at 126° → (75, 184),  hot end at 174° → (15, 80).
				-->
				<linearGradient id="grad-hotwet" gradientUnits="userSpaceOnUse" x1="75" y1="184" x2="15" y2="80">
					<stop offset="0%" class="stop-wet" />
					<stop offset="100%" class="stop-hot" />
				</linearGradient>
			</defs>
			<path
				v-for="seg in segments"
				:key="seg.id"
				:d="seg.path"
				:class="[
					'segment',
					seg.id,
					{ selected: model === seg.id, hovered: hoveredId === seg.id },
				]"
				@click="select(seg.id)"
				@mouseenter="hoveredId = seg.id"
				@mouseleave="hoveredId = null"
				v-tooltip.bottom="seg.tooltip"
				:aria-label="seg.tooltip"
				:aria-pressed="model === seg.id"
			/>
		</svg>

		<!-- icons are rendered here -->
		<div
			v-for="seg in segments"
			:key="'btn-' + seg.id"
			class="seg-icon"
			:class="{ combined: seg.combined }"
			:style="{ left: pct(seg.cx), top: pct(seg.cy) }"
		>
			<component
				v-for="(icon, i) in seg.icons"
				:key="i"
				:is="icon"
				aria-hidden="true"
			/>
		</div>
	</div>
</template>

<style scoped lang="scss">
.ring-container {
	position: relative;
	width: 12rem;
	height: 12rem;
	margin: 0 auto;

	.ring-svg {
		width: 100%;
		height: 100%;

		// SVG gradient stop colours via CSS custom props
		.stop-hot {
			stop-color: var(--theme-hot-primary-glass);
		}
		.stop-cold {
			stop-color: var(--theme-cold-primary-glass);
		}
		.stop-wet {
			stop-color: var(--theme-wet-primary-glass);
		}

		.segment {
			pointer-events: all;
			cursor: pointer;
			transition: filter 0.15s;
			stroke: transparent;
			stroke-width: 0;

			&.hot {
				fill: var(--theme-hot-primary-glass);
			}
			&.cold {
				fill: var(--theme-cold-primary-glass);
			}
			&.wet {
				fill: var(--theme-wet-primary-glass);
			}
			&.hotcold {
				fill: url(#grad-hotcold);
			}
			&.coldwet {
				fill: url(#grad-coldwet);
			}
			&.hotwet {
				fill: url(#grad-hotwet);
			}

			&.hovered {
				filter: brightness(1.25);
			}
			&.selected {
				filter: brightness(1.45);
				stroke: rgba(255, 255, 255, 0.75);
				stroke-width: 1.5;
			}
		}
	}

	.seg-icon {
		position: absolute;
		transform: translate(-50%, -50%);
		background: transparent;
		border: none;
		padding: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.05rem;
		color: white;
		line-height: 0;
		pointer-events: none; // icons are decorative only, all interaction is via the SVG paths


		:deep(svg) {
			display: block;
		}

		// Single types: larger icon
		&:not(.combined) :deep(svg) {
			width: 2rem;
			height: 2rem;
		}

		// Combined types: two smaller icons
		&.combined :deep(svg) {
			width: 1.5rem;
			height: 1.5rem;
		}
		&.combined :deep(svg:first-child) {
			transform: translateX(30%);
			clip-path: inset(0 30% 0 0);
		}
		&.combined :deep(svg:last-child) {
			transform: translateX(-30%);
			clip-path: inset(0 0 0 30%);
		}
	}
}
</style>
