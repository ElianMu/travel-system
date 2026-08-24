<template>
  <div>
    <div class="search-bar">
      <el-input v-model="query" placeholder="搜索景点，如：三亚有哪些必去景点" class="q" @keyup.enter="doSearch" />
      <el-input v-model="city" placeholder="城市（可选）" class="city" @keyup.enter="doSearch" />
      <el-button type="primary" @click="doSearch">搜索</el-button>
    </div>
    <div v-loading="loading">
      <el-empty v-if="!loading && results.length === 0" description="暂无结果，请输入查询" />
      <SearchResultCard v-for="h in results" :key="h.id" :hit="h" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchAttractions } from '../api'
import SearchResultCard from '../components/SearchResultCard.vue'

const query = ref('')
const city = ref('')
const results = ref([])
const loading = ref(false)

async function doSearch() {
  if (!query.value) return
  loading.value = true
  try {
    const data = await searchAttractions({ query: query.value, city: city.value || undefined })
    results.value = data.results || []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.q {
  flex: 1;
}
.city {
  width: 180px;
}
</style>
