<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';

const props = defineProps<{
  size: number;
  coords: { x: number; y: number; z: number };
  dataValues: number[];
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);

function draw() {
  const canvas = canvasRef.value;
  if (!canvas) return;

  const ctx = canvas.getContext('2d')!;
  const pixelSize = 4;
  const pixelsPerRow = props.size / pixelSize;

  for (let i = 0; i < props.dataValues.length; i++) {
    const val = props.dataValues[i];
    const x = (i % pixelsPerRow) * pixelSize;
    const y = Math.floor(i / pixelsPerRow) * pixelSize;

    const r = Math.floor(255 * val);
    const b = 255 - r;
    ctx.fillStyle = `rgb(${r},0,${b})`;
    ctx.fillRect(x, y, pixelSize, pixelSize);
  }
}

onMounted(draw);
watch(() => props.dataValues, draw, { deep: true });
</script>

<template>
  <canvas
    ref="canvasRef"
    :width="size"
    :height="size"
    style="position: absolute; top: 0; left: 0;"
  />
</template>
