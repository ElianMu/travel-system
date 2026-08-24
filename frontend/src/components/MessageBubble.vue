<template>
  <div :class="['bubble', message.role]">
    <div v-if="message.role === 'assistant' && !message.content" class="content thinking">
      正在思考<span class="dots"><span>.</span><span>.</span><span>.</span></span>
    </div>
    <div v-else class="content">{{ message.content }}</div>
    <CitationList v-if="message.role === 'assistant' && message.citations?.length" :citations="message.citations" />
  </div>
</template>

<script setup>
import CitationList from './CitationList.vue'

defineProps({ message: { type: Object, required: true } })
</script>

<style scoped>
.bubble {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
}
.bubble.user {
  align-items: flex-end;
}
.bubble.user .content {
  background: #409eff;
  color: #fff;
  border-radius: 8px;
  padding: 10px 14px;
  max-width: 70%;
}
.bubble.assistant .content {
  background: #f5f7fa;
  color: #303133;
  border-radius: 8px;
  padding: 10px 14px;
  max-width: 85%;
  white-space: pre-wrap;
  line-height: 1.6;
}
.thinking {
  color: #909399;
  font-style: italic;
}
.dots span {
  animation: blink 1.4s infinite both;
}
.dots span:nth-child(2) {
  animation-delay: 0.2s;
}
.dots span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0;
  }
  40% {
    opacity: 1;
  }
}
</style>
