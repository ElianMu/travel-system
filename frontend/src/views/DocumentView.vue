<template>
  <div>
    <div class="search-bar">
      <el-input v-model="filters.content_type" placeholder="内容类型" class="w" @keyup.enter="load" />
      <el-input v-model="filters.region" placeholder="地区" class="w" @keyup.enter="load" />
      <el-input v-model="filters.name" placeholder="名称" class="w" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>
    <el-table :data="documents" v-loading="loading" border>
      <el-table-column prop="source_file" label="来源文件" min-width="160" />
      <el-table-column prop="content_type" label="类型" width="100" />
      <el-table-column prop="region" label="地区" width="120" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="theme" label="主题" min-width="180" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { listDocuments } from '../api'

const documents = ref([])
const loading = ref(false)
const filters = reactive({ content_type: '', region: '', name: '' })

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.content_type) params.content_type = filters.content_type
    if (filters.region) params.region = filters.region
    if (filters.name) params.name = filters.name
    const data = await listDocuments(params)
    documents.value = data.documents || []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.w {
  width: 180px;
}
</style>
