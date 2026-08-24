<template>
  <div :class="['bubble', message.role]">
    <div class="content">{{ message.content }}</div>
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
</style>
