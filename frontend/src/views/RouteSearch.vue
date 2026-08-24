<template>
  <div class="search-page">
    <div class="results" v-loading="loading">
      <el-empty v-if="!loading && results.length === 0" description="请输入查询，如：三亚 5 日游" />
      <SearchResultCard v-for="h in results" :key="h.id" :hit="h" />
    </div>
    <div class="search-bar">
      <el-input v-model="query" placeholder="搜索线路，如：三亚 5 日游" class="q" @keyup.enter="doSearch" />
      <el-input v-model="region" placeholder="地区（可选）" class="city" @keyup.enter="doSearch" />
      <el-button type="primary" @click="doSearch">搜索</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onActivated } from 'vue'
import { searchRoutes } from '../api'
import SearchResultCard from '../components/SearchResultCard.vue'

const query = ref('')
const region = ref('')
const results = ref([])
const loading = ref(false)

async function doSearch() {
  if (!query.value) return
  loading.value = true
  try {
    const data = await searchRoutes({ query: query.value, region: region.value || undefined })
    results.value = data.results || []
  } finally {
    loading.value = false
  }
}

let timer = null
watch([query, region], () => {
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
.city {
  width: 180px;
}
</style>
