<script lang="ts" setup>
import Panel from './Panel.vue';
</script>

<template>
    <Panel class="windowed-panel" :active="true">
        <div class="top frame"></div>
        <div class="right frame"></div>
        <div class="left frame"></div>
        <div class="bottom frame"></div>
        <div ref="windowRef" class="window">
        </div>
        <div class="panel frame">
            <slot></slot>
        </div>
    </Panel>
</template>
