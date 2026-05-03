<script setup>
import { ref } from 'vue'
import { NButton, NCard, NInput, NInputNumber, NList, NListItem } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: 'AI知识库' })

const question = ref('')
const topK = ref(5)
const answer = ref('')
const references = ref([])
const loading = ref(false)
const streamLoading = ref(false)
const feedbackScore = ref(5)
const feedbackComment = ref('')

async function ask() {
  const q = question.value.trim()
  if (!q) {
    $message.warning('请输入问题')
    return
  }
  loading.value = true
  try {
    const res = await api.aiKbChat({ question: q, top_k: topK.value })
    answer.value = res?.data?.answer || ''
    references.value = res?.data?.references || []
  } finally {
    loading.value = false
  }
}

async function askByStream() {
  const q = question.value.trim()
  if (!q) {
    $message.warning('请输入问题')
    return
  }
  streamLoading.value = true
  answer.value = ''
  references.value = []
  try {
    const url = `/api/v1/ai-kb/chat/stream?question=${encodeURIComponent(q)}&top_k=${encodeURIComponent(topK.value)}`
    const evt = new EventSource(url)
    await new Promise((resolve) => {
      evt.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'meta') {
            references.value = payload.references || []
          } else if (payload.type === 'delta') {
            answer.value += payload.content || ''
          } else if (payload.type === 'done') {
            evt.close()
            resolve(true)
          }
        } catch {
          evt.close()
          resolve(true)
        }
      }
      evt.onerror = () => {
        evt.close()
        resolve(true)
      }
    })
  } finally {
    streamLoading.value = false
  }
}

async function submitFeedback() {
  if (!question.value || !answer.value) {
    $message.warning('请先完成一次问答')
    return
  }
  await api.aiKbFeedback({
    question: question.value,
    answer: answer.value,
    score: feedbackScore.value,
    comment: feedbackComment.value,
  })
  feedbackComment.value = ''
  $message.success('反馈已提交')
}

</script>

<template>
  <CommonPage title="AI知识库" show-footer>
    <NCard title="智能问答" size="small">
      <NInput v-model:value="question" type="textarea" :rows="4" placeholder="请输入产品功能问题" />
      <div style="display:flex; gap:12px; margin-top:12px; align-items:center;">
        <span>TopK</span>
        <NInputNumber v-model:value="topK" :min="1" :max="20" />
        <NButton type="primary" :loading="loading" @click="ask">提问</NButton>
        <NButton :loading="streamLoading" @click="askByStream">流式提问</NButton>
      </div>
      <NCard v-if="answer" title="回答" size="small" style="margin-top:12px;">
        <div style="white-space:pre-wrap;">{{ answer }}</div>
      </NCard>
      <NCard v-if="references.length" title="参考来源" size="small" style="margin-top:12px;">
        <NList>
          <NListItem v-for="(item, idx) in references" :key="idx">{{ item.title }} ({{ item.score }})</NListItem>
        </NList>
      </NCard>
    </NCard>

    <NCard title="反馈优化" size="small" style="margin-top:12px;">
      <div style="display:flex; gap:12px; align-items:center;">
        <span>评分</span>
        <NInputNumber v-model:value="feedbackScore" :min="1" :max="5" />
      </div>
      <NInput v-model:value="feedbackComment" type="textarea" :rows="3" placeholder="补充建议（可选）" style="margin-top:8px;" />
      <NButton type="primary" style="margin-top:8px;" @click="submitFeedback">提交反馈</NButton>
    </NCard>
  </CommonPage>
</template>
