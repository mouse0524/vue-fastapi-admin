<script setup>
import { ref } from 'vue'
import { NButton, NInputNumber, NSpace } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '会话记录' })

const sessionTableRef = ref(null)
const messageTableRef = ref(null)
const sessionQuery = ref({})
const selectedSessionId = ref(null)
const selectedSpaceId = ref(null)
const messages = ref([])

const sessionColumns = [
  { title: '会话ID', key: 'id', width: 90, align: 'center' },
  { title: '空间ID', key: 'space_id', width: 90, align: 'center' },
  { title: '标题', key: 'title', align: 'left' },
  { title: '状态', key: 'status', width: 80, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 180, align: 'center' },
]

const messageColumns = [
  { title: '消息ID', key: 'id', width: 90, align: 'center' },
  { title: '角色', key: 'role', width: 80, align: 'center' },
  { title: '模型', key: 'model_name', width: 120, align: 'center' },
  { title: '输入Token', key: 'prompt_tokens', width: 100, align: 'center' },
  { title: '输出Token', key: 'completion_tokens', width: 100, align: 'center' },
  { title: '耗时(ms)', key: 'latency_ms', width: 90, align: 'center' },
  { title: '内容', key: 'content', align: 'left' },
  { title: '时间', key: 'created_at', width: 180, align: 'center' },
]

async function getSessionData(params = {}) {
  const res = await api.kbSessionList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

async function getMessageData() {
  return {
    data: messages.value,
    total: messages.value.length,
  }
}

async function loadMessages(sessionId) {
  if (!sessionId) return
  const res = await api.kbSessionMessages({ session_id: sessionId })
  messages.value = res?.data || []
  messageTableRef.value?.handleSearch()
}

async function onSessionClick(row) {
  selectedSessionId.value = row.id
  selectedSpaceId.value = row.space_id
  await loadMessages(row.id)
}

async function manualLoad() {
  await loadMessages(selectedSessionId.value)
}
</script>

<template>
  <CommonPage title="会话记录" show-footer>
    <NSpace vertical>
      <CrudTable
        ref="sessionTableRef"
        v-model:query-items="sessionQuery"
        :columns="sessionColumns"
        :get-data="getSessionData"
        :row-props="(row) => ({ onClick: () => onSessionClick(row), style: 'cursor:pointer;' })"
      />

      <NSpace align="center">
        <NInputNumber v-model:value="selectedSessionId" :min="1" placeholder="会话ID" style="width: 150px" />
        <NInputNumber v-model:value="selectedSpaceId" :min="1" placeholder="空间ID" style="width: 150px" disabled />
        <NButton type="primary" @click="manualLoad">加载消息</NButton>
      </NSpace>

      <CrudTable
        ref="messageTableRef"
        :columns="messageColumns"
        :is-pagination="false"
        :remote="false"
        :get-data="getMessageData"
      />
    </NSpace>
  </CommonPage>
</template>
