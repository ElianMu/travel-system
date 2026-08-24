<template>
  <div class="citations">
    <div class="label">引用来源</div>
    <div v-for="(c, i) in citations" :key="i" class="cite">
      [{{ i + 1 }}] {{ c.source_file }}<span v-if="c.heading_path">（{{ c.heading_path }}）</span>
    </div>
  </div>
</template>

<script setup>
defineProps({ citations: { type: Array, default: () => [] } })
</script>

<style scoped>
.citations {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}
.label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.cite {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}
</style>
