<script setup>
import { computed, ref } from 'vue'
import { NButton, NCard, NInput, NInputNumber, NSpace } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '智能问答' })

const spaceId = ref(null)
const question = ref('')
const sessionId = ref(null)
const loading = ref(false)
const answer = ref('')
const citations = ref([])
const answerModel = ref('')
const answerLatency = ref(null)
const promptTokens = ref(null)
const completionTokens = ref(null)
const sessionTableRef = ref(null)
const sessionQuery = ref({})

const canAsk = computed(() => Number(spaceId.value) > 0 && !!question.value.trim())

async function ask() {
  if (!canAsk.value) {
    $message.warning('请填写空间ID和问题')
    return
  }
  try {
    loading.value = true
    const res = await api.kbChatAsk({
      space_id: Number(spaceId.value),
      question: question.value.trim(),
      session_id: sessionId.value || null,
    })
    const data = res?.data || {}
    sessionId.value = data.session_id || sessionId.value
    answer.value = data.answer || ''
    citations.value = data.citations || []
    answerModel.value = data.model || ''
    answerLatency.value = data.latency_ms ?? null
    promptTokens.value = data.prompt_tokens ?? null
    completionTokens.value = data.completion_tokens ?? null
    sessionTableRef.value?.handleSearch()
  } finally {
    loading.value = false
  }
}

const sessionColumns = [
  { title: '会话ID', key: 'id', width: 90, align: 'center' },
  { title: '空间ID', key: 'space_id', width: 90, align: 'center' },
  { title: '标题', key: 'title', align: 'left' },
  { title: '状态', key: 'status', width: 80, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 170, align: 'center' },
]

async function getSessionData(params = {}) {
  const res = await api.kbSessionList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

function onSessionRowClick(row) {
  sessionId.value = row.id
  spaceId.value = row.space_id
  $message.success(`已切换会话 #${row.id}`)
}
</script>

<template>
  <CommonPage title="智能问答" show-footer>
    <NSpace vertical>
      <NCard size="small" title="历史会话">
        <CrudTable
          ref="sessionTableRef"
          v-model:query-items="sessionQuery"
          :columns="sessionColumns"
          :get-data="getSessionData"
          :row-props="(row) => ({ onClick: () => onSessionRowClick(row), style: 'cursor:pointer;' })"
        />
      </NCard>

      <NSpace>
        <NInputNumber v-model:value="spaceId" :min="1" placeholder="空间ID" style="width: 160px" />
        <NInputNumber v-model:value="sessionId" :min="1" placeholder="会话ID(可选)" style="width: 180px" />
      </NSpace>
      <NInput
        v-model:value="question"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 6 }"
        placeholder="输入你的问题"
      />
      <NButton type="primary" :loading="loading" :disabled="!canAsk" @click="ask">提问</NButton>

      <NCard size="small" title="回答">
        <NSpace vertical>
          <div style="white-space: pre-wrap; line-height: 1.7;">{{ answer || '暂无回答' }}</div>
          <div v-if="answer" class="answer-meta">
            <span>model: {{ answerModel || '-' }}</span>
            <span>latency: {{ answerLatency ?? '-' }} ms</span>
            <span>prompt_tokens: {{ promptTokens ?? '-' }}</span>
            <span>completion_tokens: {{ completionTokens ?? '-' }}</span>
          </div>
        </NSpace>
      </NCard>

      <NCard size="small" title="引用来源">
        <div v-if="!citations.length">暂无引用</div>
        <NSpace v-else vertical>
          <div v-for="item in citations" :key="item.id || item.chunk_id" class="citation-item">
            <div>文档ID: {{ item.document_id }} | 分块ID: {{ item.chunk_id }} | 分值: {{ item.score }}</div>
            <div class="snippet">{{ item.snippet }}</div>
          </div>
        </NSpace>
      </NCard>
    </NSpace>
  </CommonPage>
</template>

<style scoped>
.citation-item {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.snippet {
  margin-top: 6px;
  color: #4b5563;
  white-space: pre-wrap;
}

.answer-meta {
  display: flex;
  gap: 16px;
  color: #6b7280;
  font-size: 12px;
}
</style>
