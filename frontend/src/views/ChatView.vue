<template>
  <div class="chat-view">
    <div class="sidebar">
      <el-button type="primary" class="new-btn" @click="newSession">新建会话</el-button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.session_id"
          :class="['session-item', { active: s.session_id === sessionId }]"
          @click="selectSession(s.session_id)"
        >
          <span class="title">{{ s.title }}</span>
          <el-icon class="del" @click.stop="removeSession(s.session_id)"><Delete /></el-icon>
        </div>
      </div>
    </div>
    <div class="chat-area">
      <ChatPanel :messages="messages" :is-streaming="isStreaming" @send="send" />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import ChatPanel from '../components/ChatPanel.vue'
import { useChatStore } from '../store/chat'

const chatStore = useChatStore()
const { sessions, sessionId, messages, isStreaming } = storeToRefs(chatStore)
const { loadSessions, newSession, selectSession, removeSession, send } = chatStore

onMounted(loadSessions)
</script>

<style scoped>
.chat-view {
  display: flex;
  gap: 16px;
  height: 100%;
  overflow: hidden;
}
.sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid #e5e7eb;
  padding-right: 16px;
  display: flex;
  flex-direction: column;
}
.chat-area {
  flex: 1;
  min-width: 0;
  height: 100%;
}
.new-btn {
  width: 100%;
  margin-bottom: 12px;
}
.session-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.session-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.session-item:hover {
  background: #f5f7fa;
}
.session-item.active {
  background: #ecf5ff;
  color: #409eff;
}
.title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.del {
  visibility: hidden;
}
.session-item:hover .del {
  visibility: visible;
}
</style>
