<template>
  <el-table :data="documents" v-loading="loading" border>
    <el-table-column prop="source_file" label="来源文件" min-width="160" />
    <el-table-column prop="content_type" label="类型" width="100" />
    <el-table-column prop="region" label="地区" width="120" />
    <el-table-column prop="name" label="名称" min-width="160" />
    <el-table-column prop="theme" label="主题" min-width="180" show-overflow-tooltip />
    <el-table-column label="操作" width="150" fixed="right">
      <template #default="{ row }">
        <el-button size="small" @click="emit('view', row)">查看</el-button>
        <el-button size="small" type="danger" @click="emit('delete', row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  documents: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['view', 'delete'])
</script>
