import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)

  function reset() {
    sessionId.value = null
    messages.value = []
    isStreaming.value = false
  }

  return { sessionId, messages, isStreaming, reset }
})
