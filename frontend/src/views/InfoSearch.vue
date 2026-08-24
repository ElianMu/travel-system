<template>
  <div class="search-page">
    <el-tabs v-model="type" @tab-change="doSearch" class="tabs">
      <el-tab-pane label="酒店" name="hotel" />
      <el-tab-pane label="美食" name="food" />
      <el-tab-pane label="交通" name="transport" />
    </el-tabs>
    <div class="results" v-loading="loading">
      <el-empty v-if="!loading && results.length === 0" description="请输入查询，如：成都美食推荐" />
      <SearchResultCard v-for="h in results" :key="h.id" :hit="h" />
    </div>
    <div class="search-bar">
      <el-input v-model="query" placeholder="搜索酒店 / 美食 / 交通" class="q" @keyup.enter="doSearch" />
      <el-button type="primary" @click="doSearch">搜索</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onActivated } from 'vue'
import { searchInfo } from '../api'
import SearchResultCard from '../components/SearchResultCard.vue'

const query = ref('')
const type = ref('hotel')
const results = ref([])
const loading = ref(false)

async function doSearch() {
  if (!query.value) return
  loading.value = true
  try {
    const data = await searchInfo({ query: query.value, type: type.value })
    results.value = data.results || []
  } finally {
    loading.value = false
  }
}

let timer = null
watch([query, type], () => {
  if (!query.value.trim()) {
    results.value = []
    return
  }
  clearTimeout(timer)
  timer = setTimeout(doSearch, 400)
})

onActivated(() => {
  results.value = []
})
</script>

<style scoped>
.search-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tabs {
  flex-shrink: 0;
}
.results {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.search-bar {
  flex-shrink: 0;
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
.q {
  flex: 1;
}
</style>
