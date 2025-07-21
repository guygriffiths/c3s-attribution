<script setup>
const model = defineModel({ type: Boolean })
</script>

<template>
  <label class="toggle">
    <input type="checkbox" v-model="model" />
  </label>
</template>

<style scoped>
.toggle {
  display: flex;
  align-items: center;
}
</style>