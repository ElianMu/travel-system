<template>
  <el-card class="result-card" shadow="hover">
    <div class="title">{{ hit.name || hit.source_file || '未命名' }}</div>
    <div class="tags">
      <el-tag v-if="hit.content_type" size="small">{{ hit.content_type }}</el-tag>
      <el-tag v-if="hit.region" size="small" type="success">{{ hit.region }}</el-tag>
      <span v-if="hit.heading_path" class="heading">片段：{{ hit.heading_path }}</span>
    </div>
    <div class="content">{{ hit.content }}</div>
    <div class="source">
      来源：{{ hit.source_file }}
      <span v-if="hit.score != null"> · 相关度 {{ hit.score }}</span>
    </div>
  </el-card>
</template>

<script setup>
defineProps({ hit: { type: Object, required: true } })
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
.source {
  margin-top: 8px;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
