<script setup>
import { computed, onMounted, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '批量上传任务' })

const loading = ref(false)
const taskId = ref('')
const task = ref(null)

const progress = computed(() => {
  if (!task.value || !task.value.total) return 0
  return Math.round(((task.value.completed + task.value.failed) / task.value.total) * 100)
})

onMounted(async () => {
  const recent = localStorage.getItem('skillKnowLastBatchTaskId') || ''
  if (recent) {
    taskId.value = recent
    await queryTask()
  }
})

async function queryTask() {
  if (!taskId.value.trim()) return
  loading.value = true
  try {
    const res = await api.skillKnowUploadTask({ task_id: taskId.value.trim() })
    task.value = res.data
    localStorage.setItem('skillKnowLastBatchTaskId', taskId.value.trim())
  } finally {
    loading.value = false
  }
}

async function cleanupTask() {
  if (!task.value?.task_id) return
  await api.skillKnowDeleteUploadTask({ task_id: task.value.task_id })
  $message.success('任务已清理')
  task.value = null
}
</script>

<template>
  <CommonPage title="批量上传任务" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">批量任务监控</h2>
      <p class="sk-hero-sub">追踪批量上传文档的处理进度、失败原因与最终结果。</p>
    </div>
    <NCard :bordered="false" class="task-card">
      <NSpace>
        <NInput v-model:value="taskId" placeholder="输入任务ID，例如 8d2c..." clearable @keyup.enter="queryTask" />
        <NButton type="primary" :loading="loading" @click="queryTask">查询任务</NButton>
      </NSpace>

      <template v-if="task">
        <NDivider />
        <NGrid :cols="4" :x-gap="12">
          <NGi><NStatistic label="总文件数" :value="task.total || 0" /></NGi>
          <NGi><NStatistic label="成功" :value="task.completed || 0" /></NGi>
          <NGi><NStatistic label="失败" :value="task.failed || 0" /></NGi>
          <NGi><NStatistic label="状态" :value="task.status || '-'" /></NGi>
        </NGrid>
        <NProgress style="margin-top: 12px" type="line" :percentage="progress" />
        <NTable style="margin-top: 16px" striped>
          <thead>
            <tr>
              <th>文件名</th>
              <th>状态</th>
              <th>进度</th>
              <th>消息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in task.files || []" :key="item.filename + item.status">
              <td>{{ item.filename }}</td>
              <td>
                <NTag :type="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'error' : 'warning'">
                  {{ item.status }}
                </NTag>
              </td>
              <td>{{ item.progress || 0 }}%</td>
              <td>{{ item.message || item.error || '-' }}</td>
            </tr>
          </tbody>
        </NTable>
        <NSpace justify="end" style="margin-top: 16px">
          <NButton secondary type="error" @click="cleanupTask">清理任务</NButton>
        </NSpace>
      </template>
      <NEmpty v-else description="输入任务ID后查询" style="margin-top: 24px" />
    </NCard>
    </div>
  </CommonPage>
</template>

<style scoped>
.task-card { border-radius: 18px; }
</style>
