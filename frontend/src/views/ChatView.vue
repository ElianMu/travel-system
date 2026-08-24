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
    <ChatPanel :messages="messages" :is-streaming="isStreaming" @send="send" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { chat, chatStream, listSessions, createSession, getMessages, deleteSession } from '../api'
import ChatPanel from '../components/ChatPanel.vue'

const sessions = ref([])
const sessionId = ref(null)
const messages = ref([])
const isStreaming = ref(false)

async function loadSessions() {
  const data = await listSessions()
  sessions.value = data.sessions || []
}

async function newSession() {
  const s = await createSession('新对话')
  sessionId.value = s.session_id
  messages.value = []
  await loadSessions()
}

async function selectSession(id) {
  if (isStreaming.value) return
  sessionId.value = id
  const data = await getMessages(id)
  messages.value = (data.messages || []).map((m) => ({
    role: m.role,
    content: m.content,
    citations: m.citations || [],
  }))
}

async function removeSession(id) {
  await deleteSession(id)
  if (sessionId.value === id) {
    sessionId.value = null
    messages.value = []
  }
  await loadSessions()
}

async function send(query) {
  if (!sessionId.value) {
    const s = await createSession('新对话')
    sessionId.value = s.session_id
    await loadSessions()
  }

  messages.value.push({ role: 'user', content: query })
  const assistant = { role: 'assistant', content: '', citations: [] }
  messages.value.push(assistant)
  isStreaming.value = true

  try {
    await chatStream(
      { query, sessionId: sessionId.value },
      (delta) => {
        assistant.content += delta
      },
      (citations) => {
        assistant.citations = citations
      },
      (answer) => {
        assistant.content = answer
      },
    )
  } catch (e) {
    // 流式失败，回退非流式
    try {
      const data = await chat({ query, session_id: sessionId.value })
      assistant.content = data.answer
      assistant.citations = data.citations || []
    } catch (e2) {
      ElMessage.error('问答失败')
    }
  } finally {
    isStreaming.value = false
  }
}

onMounted(loadSessions)
</script>

<style scoped>
.chat-view {
  display: flex;
  gap: 16px;
  height: calc(100vh - 120px);
}
.sidebar {
  width: 220px;
  border-right: 1px solid #e5e7eb;
  padding-right: 16px;
}
.new-btn {
  width: 100%;
  margin-bottom: 12px;
}
.session-list {
  max-height: calc(100vh - 180px);
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
