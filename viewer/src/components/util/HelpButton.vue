<script setup lang="ts">
import { helpMe, helpText, activeHelp, closeHelp } from '@/lib/help'
import { useLabels } from '@/lib/labels';
import { IconHelp, IconHelpCircle } from '@tabler/icons-vue';

const $l = useLabels()

defineProps<{
    help: keyof typeof helpText
}>()

const toggleHelp = (e: MouseEvent, id: keyof typeof helpText) => {
    console.log('Toggling help for', id);
    if(activeHelp.value !== null) {
        // Close if already open
        closeHelp() 
    } else {
        helpMe(e, id)
    }
}
</script>

<template>
    <button
        class="help-button glassy color"
        @click="(e) => toggleHelp(e, help)"
        v-tooltip="$l.help"
    >
        <IconHelp aria-hidden="true"/>
    </button>
</template>

<style scoped>
.help-button {
    z-index: 9999;
    padding: 0;
    position: absolute;
    bottom: 0;
    right: 0;
    border-top-right-radius: 0;
    border-bottom-left-radius: 0;
    padding: 2px;

    svg {
        margin-bottom: -3px !important;
    }
}
</style>