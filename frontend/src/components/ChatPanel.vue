<template>
  <div class="chat-panel">
    <div class="messages" ref="msgRef">
      <el-empty v-if="messages.length === 0" description="开始提问吧" />
      <MessageBubble v-for="(m, i) in messages" :key="i" :message="m" />
    </div>
    <div class="input">
      <el-input
        v-model="input"
        placeholder="输入问题，如：三亚有哪些必去景点？"
        :disabled="isStreaming"
        @keyup.enter="send"
      />
      <el-button type="primary" :loading="isStreaming" @click="send">{{ isStreaming ? '思考中…' : '发送' }}</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
})
const emit = defineEmits(['send'])

const input = ref('')
const msgRef = ref(null)

function send() {
  const q = input.value.trim()
  if (!q || props.isStreaming) return
  input.value = ''
  emit('send', q)
}

watch(
  () => {
    // 同时监听消息条数与最后一条内容长度，流式增量时也能滚动到底部
    const last = props.messages[props.messages.length - 1]
    return props.messages.length * 100000 + (last ? last.content.length : 0)
  },
  async () => {
    await nextTick()
    if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight
  },
)
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.input {
  flex-shrink: 0;
  display: flex;
  gap: 12px;
  margin-top: 12px;
}
</style>
