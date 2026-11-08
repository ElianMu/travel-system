<template>
  <div>
    <el-upload :http-request="upload" :show-file-list="false" accept=".md,.markdown" multiple>
      <el-button type="primary">上传文档（Markdown，可多选）</el-button>
    </el-upload>
    <el-table v-if="tasks.length" :data="tasks" border class="tasks">
      <el-table-column prop="file_name" label="文件" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS[row.status].tag">{{ STATUS[row.status].text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="160">
        <template #default="{ row }">{{ row.processed_chunks }} / {{ row.total_chunks }} 片段</template>
      </el-table-column>
      <el-table-column prop="error_message" label="失败原因" min-width="240" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getImportTask, importDocument } from '../api'

const POLL_INTERVAL_MS = 1000
const STATUS = {
  uploading: { text: '上传中', tag: 'info' },
  created: { text: '排队中', tag: 'info' },
  running: { text: '进行中', tag: 'warning' },
  success: { text: '成功', tag: 'success' },
  failed: { text: '失败', tag: 'danger' },
}

const tasks = ref([])

async function upload({ file }) {
  const task = reactive({
    file_name: file.name,
    status: 'uploading',
    total_chunks: 0,
    processed_chunks: 0,
    error_message: '',
  })
  tasks.value.unshift(task)

  try {
    const formData = new FormData()
    formData.append('file', file)
    const { task_id: taskId } = await importDocument(formData)
    await pollUntilFinished(taskId, task)
  } catch (err) {
    task.status = 'failed'
    task.error_message = err.response?.data?.message || '导入异常'
  }
  notify(task)
}

async function pollUntilFinished(taskId, task) {
  while (true) {
    Object.assign(task, await getImportTask(taskId))
    if (task.status === 'success' || task.status === 'failed') return
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
  }
}

function notify(task) {
  if (task.status === 'success') {
    ElMessage.success(`${task.file_name} 导入成功（${task.processed_chunks} 片段）`)
  } else {
    ElMessage.error(`${task.file_name} 导入失败`)
  }
}
</script>

<style scoped>
.tasks {
  margin-top: 16px;
}
</style>
