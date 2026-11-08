import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chat, chatStream, createSession, deleteSession, getMessages, listSessions } from '../api'

const MAX_TITLE_LENGTH = 20

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const sessionId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)

  async function loadSessions() {
    const data = await listSessions()
    sessions.value = data.sessions || []
  }

  /** 新建空白会话：清空当前，输入第一个问题后才真正创建（豆包式交互） */
  function newSession() {
    if (isStreaming.value) return
    sessionId.value = null
    messages.value = []
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
    if (isStreaming.value && sessionId.value === id) return
    await deleteSession(id)
    if (sessionId.value === id) {
      sessionId.value = null
      messages.value = []
    }
    await loadSessions()
  }

  async function ensureSession(query) {
    if (sessionId.value) return
    const title = query.length > MAX_TITLE_LENGTH ? `${query.slice(0, MAX_TITLE_LENGTH)}…` : query
    const session = await createSession(title)
    sessionId.value = session.session_id
    await loadSessions()
  }

  async function send(query) {
    isStreaming.value = true
    try {
      await ensureSession(query)
      messages.value.push({ role: 'user', content: query })
      messages.value.push({ role: 'assistant', content: '', citations: [] })
      // 从响应式数组取回代理对象，直接修改原始对象不会触发渲染
      await answer(query, messages.value[messages.value.length - 1])
    } finally {
      isStreaming.value = false
    }
  }

  async function answer(query, assistant) {
    try {
      await chatStream(
        { query, sessionId: sessionId.value },
        (delta) => {
          assistant.content += delta
        },
        (citations) => {
          assistant.citations = citations
        },
        (fullAnswer) => {
          assistant.content = fullAnswer
        },
      )
    } catch {
      await answerWithoutStreaming(query, assistant)
    }
  }

  /** 流式失败时回退非流式接口 */
  async function answerWithoutStreaming(query, assistant) {
    try {
      const data = await chat({ query, session_id: sessionId.value })
      assistant.content = data.answer
      assistant.citations = data.citations || []
    } catch {
      assistant.content = '问答失败，请稍后重试。'
      ElMessage.error('问答失败')
    }
  }

  return {
    sessions,
    sessionId,
    messages,
    isStreaming,
    loadSessions,
    newSession,
    selectSession,
    removeSession,
    send,
  }
})
