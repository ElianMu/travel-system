<template>
  <div class="doc-page">
    <div class="search-bar">
      <el-select v-model="filters.content_type" placeholder="内容类型" class="w" clearable>
        <el-option v-for="t in CONTENT_TYPES" :key="t" :label="t" :value="t" />
      </el-select>
      <el-input v-model="filters.region" placeholder="地区" class="w" clearable @keyup.enter="load" />
      <el-input v-model="filters.name" placeholder="名称" class="w" clearable @keyup.enter="load" />
      <el-input v-model="filters.source_file" placeholder="来源文件" class="w" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </div>
    <MetadataTable :documents="documents" :loading="loading" @view="viewDetail" @delete="remove" />

    <el-dialog v-model="detailVisible" title="文档详情" width="720px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="来源文件">{{ detail.source_file }}</el-descriptions-item>
          <el-descriptions-item label="内容类型">{{ detail.content_type }}</el-descriptions-item>
          <el-descriptions-item label="地区">{{ detail.region || '-' }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detail.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主题" :span="2">{{ detail.theme || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="chunks">
          <div v-for="c in detail.chunks" :key="c.chunk_index" class="chunk">
            <div class="chunk-head">{{ c.heading_path || '片段 ' + (c.chunk_index + 1) }}</div>
            <div class="chunk-body">{{ c.content }}</div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDocuments, getDocumentDetail, deleteDocument } from '../api'
import MetadataTable from '../components/MetadataTable.vue'

const CONTENT_TYPES = ['景点介绍', '线路推荐', '酒店信息', '美食介绍', '交通指南', '文化民俗']

const documents = ref([])
const loading = ref(false)
const filters = reactive({ content_type: '', region: '', name: '', source_file: '' })

const detailVisible = ref(false)
const detail = ref(null)

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.content_type) params.content_type = filters.content_type
    if (filters.region) params.region = filters.region
    if (filters.name) params.name = filters.name
    if (filters.source_file) params.source_file = filters.source_file
    const data = await listDocuments(params)
    documents.value = data.documents || []
  } finally {
    loading.value = false
  }
}

async function viewDetail(row) {
  detail.value = await getDocumentDetail(row.id)
  detailVisible.value = true
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.source_file}」吗？删除后不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await deleteDocument(row.id)
  ElMessage.success('删除成功')
  await load()
}

let timer = null
watch(
  filters,
  () => {
    clearTimeout(timer)
    timer = setTimeout(load, 400)
  },
  { deep: true },
)

onMounted(load)
</script>

<style scoped>
.doc-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.w {
  width: 180px;
}
.chunks {
  margin-top: 16px;
  max-height: 50vh;
  overflow-y: auto;
  border-top: 1px solid #e5e7eb;
  padding-top: 12px;
}
.chunk {
  margin-bottom: 12px;
}
.chunk-head {
  font-weight: 600;
  color: #409eff;
  font-size: 13px;
  margin-bottom: 4px;
}
.chunk-body {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
