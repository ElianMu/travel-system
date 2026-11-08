<template>
  <el-card class="result-card" shadow="hover">
    <div class="title">{{ hit.name || hit.source_file || '未命名' }}</div>
    <div class="tags">
      <el-tag v-if="hit.content_type" size="small">{{ hit.content_type }}</el-tag>
      <el-tag v-if="hit.region" size="small" type="success">{{ hit.region }}</el-tag>
      <el-tag v-if="hit.source === 'web'" size="small" type="warning">联网结果</el-tag>
      <span v-if="hit.theme" class="heading">主题：{{ hit.theme }}</span>
      <span v-if="hit.heading_path" class="heading">片段：{{ hit.heading_path }}</span>
    </div>
    <div class="content">{{ hit.content }}</div>
    <el-collapse v-if="details.length" class="details">
      <el-collapse-item title="结构化信息">
        <div v-for="[label, value] in details" :key="label" class="detail">
          <div class="label">{{ label }}</div>
          <div class="value">{{ value }}</div>
        </div>
      </el-collapse-item>
    </el-collapse>
    <div class="source">
      来源：{{ hit.source_file }}
      <span v-if="hit.score != null"> · 相关度 {{ hit.score }}</span>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ hit: { type: Object, required: true } })
// 文档没有对应章节的字段为空，不展示
const details = computed(() => Object.entries(props.hit.details || {}).filter(([, value]) => value))
</script>

<style scoped>
.result-card {
  margin-bottom: 12px;
}
.title {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 8px;
}
.tags {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.heading {
  color: #909399;
  font-size: 13px;
}
.content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  max-height: 120px;
  overflow: hidden;
}
.details {
  margin-top: 8px;
}
.detail {
  margin-bottom: 8px;
}
.label {
  font-weight: 600;
  font-size: 13px;
}
.value {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.source {
  margin-top: 8px;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
