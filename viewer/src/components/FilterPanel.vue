<script setup>
import { ref, watch } from 'vue'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faFilter } from '@fortawesome/free-solid-svg-icons'

import Toggle from './common/Toggle.vue'
import FilterSlider from './common/FilterSlider.vue'
import { useLabels } from '@/lib/labels'

const $l = useLabels()

const props = defineProps({
  filters: {
    type: Array,
    required: true,
    // Example: [{ key: 'duration', label: 'Duration', type: 'range', min: 0, max: 100 }]
  },
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue'])

const values = ref({})

// Initialise filter values
props.filters.forEach(({ key, type }) => {
  values.value[key] = props.modelValue[key] ?? (
    type === 'toggle' ? false : null
  )
})

watch(values, () => {
  emit('update:modelValue', { ...values.value })
}, { deep: true })
</script>

<template>
  <div class="filter-panel">
    <div class="header">
      <FontAwesomeIcon :icon="faFilter" />
      <span class="title">{{ $l.filter }}</span>
    </div>

    <div class="filters">
      <div class="filter-row" v-for="f in props.filters" :key="f.key">
        <div class="label">{{ f.label }}</div>

        <FilterSlider
          v-if="f.type === 'range'"
          v-model="values[f.key]"
          :type="f.pass ?? 'high-pass'"
          :min="f.min"
          :max="f.max"
        />
        <Toggle
          v-else-if="f.type === 'toggle'"
          v-model="values[f.key]"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  font-family: sans-serif;
  max-width: 400px;
}

.header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: bold;
  font-size: 1.25rem;
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.filter-row {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  gap: 0.25rem;
}

.label {
  font-weight: 500;
}
</style>
