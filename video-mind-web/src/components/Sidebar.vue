<template>
    <aside class="sidebar">
<div class="profile-section">
    <ProfileCard :user-name="userName" :user-uid="userUid" @turn-to-options="$emit('turnToOptions')" />
    </div>
    <HistoryList :list="historyList" :active-id="activeHistoryId" @select="$emit('selectHistory', $event)" />
    </aside>
</template>

<script setup lang="ts">
import ProfileCard from './ProfileCard.vue'
import HistoryList from './HistoryList.vue'
import type { HistoryItem } from '../composables/useHistory'

defineProps<{
    userName: string
    userUid: string
    historyList: HistoryItem[]
    activeHistoryId: number | null
}>()

defineEmits(['turnToOptions', 'selectHistory'])
</script>

<style scoped>
.sidebar {
    width: 350px;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
}
.profile-section {
    padding: 20px;
    border-bottom: 1px solid var(--border);
}
</style>