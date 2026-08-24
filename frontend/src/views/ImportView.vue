<template>
  <div>
    <el-upload :http-request="doUpload" :show-file-list="false" :disabled="uploading">
      <el-button type="primary" :loading="uploading">上传文档（Markdown）</el-button>
    </el-upload>
    <div v-if="uploading" class="tip">正在导入，首次导入需加载模型，约 1 分钟…</div>
    <div v-if="task" class="task">
      <el-tag :type="tagType">{{ statusText }}</el-tag>
      <el-alert v-if="task.error_message" type="error" :title="task.error_message" :closable="false" class="err" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { importDocument, getImportTask } from '../api'

const uploading = ref(false)
const task = ref(null)

async function doUpload({ file }) {
  uploading.value = true
  task.value = null
  try {
    const formData = new FormData()
    formData.append('file', file)
    const data = await importDocument(formData)
    const t = await getImportTask(data.task_id)
    task.value = t
    if (t.status === 'success') {
      ElMessage.success(`导入成功（${t.processed_chunks} 片段）`)
    } else {
      ElMessage.error('导入失败')
    }
  } catch (e) {
    ElMessage.error('导入异常')
  } finally {
    uploading.value = false
  }
}

const statusText = computed(
  () => ({ created: '排队中', running: '进行中', success: '成功', failed: '失败' }[task.value?.status] || ''),
)
const tagType = computed(
  () => ({ created: 'info', running: 'warning', success: 'success', failed: 'danger' }[task.value?.status] || 'info'),
)
</script>

<style scoped>
.tip {
  margin: 12px 0;
  color: #909399;
}
.task {
  margin-top: 12px;
}
.err {
  margin-top: 12px;
}
</style>
