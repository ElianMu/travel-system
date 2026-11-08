<template>
  <div :class="['bubble', message.role]">
    <div v-if="message.role === 'assistant' && !message.content" class="content thinking">
      正在思考<span class="dots"><span>.</span><span>.</span><span>.</span></span>
    </div>
    <!-- html:false 转义模型输出中的原始 HTML，渲染结果可安全用于 v-html -->
    <div v-else-if="message.role === 'assistant'" class="content markdown" v-html="rendered" />
    <div v-else class="content">{{ message.content }}</div>
    <CitationList v-if="message.role === 'assistant' && message.citations?.length" :citations="message.citations" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import CitationList from './CitationList.vue'

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })

const props = defineProps({ message: { type: Object, required: true } })
const rendered = computed(() => markdown.render(props.message.content))
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
  line-height: 1.6;
}
.markdown :deep(p),
.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 0 0 8px;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  padding-left: 20px;
}
.markdown :deep(h1),
.markdown :deep(h2),
.markdown :deep(h3),
.markdown :deep(h4) {
  margin: 8px 0;
  font-size: 15px;
}
.markdown :deep(*:last-child) {
  margin-bottom: 0;
}
.markdown :deep(table) {
  border-collapse: collapse;
  margin-bottom: 8px;
}
.markdown :deep(th),
.markdown :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.markdown :deep(code) {
  background: #e9ecef;
  border-radius: 3px;
  padding: 1px 4px;
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
