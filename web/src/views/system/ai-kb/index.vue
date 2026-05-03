<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { NAvatar, NButton, NCard, NCollapse, NCollapseItem, NInput, NInputNumber, NRate, NSpace, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import { getToken } from '@/utils'

defineOptions({ name: 'AI知识库' })

const question = ref('')
const topK = ref(5)
const asking = ref(false)
const streamAsking = ref(false)
const messages = ref([])
const chatWindowRef = ref(null)
const currentStreamController = ref(null)
const feedbackVisible = ref(false)
const feedbackScore = ref(5)
const feedbackComment = ref('')
const refsCollapsed = ref([])
const SESSION_KEY = 'ai-kb-chat-session-v1'

const canSubmit = computed(() => !!question.value.trim() && !asking.value && !streamAsking.value)

function persistSession() {
  try {
    const payload = {
      question: question.value,
      topK: topK.value,
      messages: messages.value,
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(payload))
  } catch {
    // ignore
  }
}

function restoreSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    question.value = data?.question || ''
    topK.value = Number(data?.topK || 5)
    messages.value = Array.isArray(data?.messages) ? data.messages : []
  } catch {
    // ignore
  }
}

async function scrollToBottom() {
  await nextTick()
  const el = chatWindowRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

function pushUserMessage(content) {
  messages.value.push({ role: 'user', content, ts: new Date().toLocaleTimeString() })
  persistSession()
  scrollToBottom()
}

function pushAssistantMessage(content = '') {
  const msg = { role: 'assistant', content, refs: [], ts: new Date().toLocaleTimeString(), thinking: false }
  messages.value.push(msg)
  persistSession()
  scrollToBottom()
  return msg
}

function onAskKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (canSubmit.value) askByStream()
  }
}

function openFeedback() {
  const lastUser = [...messages.value].reverse().find((m) => m.role === 'user')
  const lastAssistant = [...messages.value].reverse().find((m) => m.role === 'assistant')
  if (!lastUser || !lastAssistant || !lastAssistant.content) {
    $message.warning('请先完成一次问答')
    return
  }
  feedbackVisible.value = true
}

function clearSession() {
  messages.value = []
  question.value = ''
  feedbackVisible.value = false
  feedbackComment.value = ''
  feedbackScore.value = 5
  refsCollapsed.value = []
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore
  }
  $message.success('会话已清空')
}

async function copyAnswer(content) {
  const text = String(content || '').trim()
  if (!text) {
    $message.warning('暂无可复制内容')
    return
  }
  await navigator.clipboard.writeText(text)
  $message.success('答案已复制')
}

async function submitFeedback() {
  const lastUser = [...messages.value].reverse().find((m) => m.role === 'user')
  const lastAssistant = [...messages.value].reverse().find((m) => m.role === 'assistant')
  if (!lastUser || !lastAssistant) return
  await api.aiKbFeedback({
    question: lastUser.content,
    answer: lastAssistant.content,
    score: feedbackScore.value,
    comment: feedbackComment.value,
  })
  feedbackVisible.value = false
  feedbackComment.value = ''
  feedbackScore.value = 5
  persistSession()
  $message.success('评价已提交')
}

async function ask() {
  const q = question.value.trim()
  if (!q) {
    $message.warning('请输入问题')
    return
  }
  asking.value = true
  currentReferences.value = []
  pushUserMessage(q)
  const assistant = pushAssistantMessage('')
  question.value = ''
  try {
    const res = await api.aiKbChat({ question: q, top_k: topK.value })
    assistant.content = res?.data?.answer || ''
    assistant.refs = res?.data?.references || []
    persistSession()
    await scrollToBottom()
  } finally {
    asking.value = false
  }
}

async function askByStream() {
  const q = question.value.trim()
  if (!q) {
    $message.warning('请输入问题')
    return
  }
  streamAsking.value = true
  pushUserMessage(q)
  const assistant = pushAssistantMessage('')
  assistant.thinking = true
  question.value = ''

  try {
    const token = getToken()
    const url = `/api/v1/ai-kb/chat/stream?question=${encodeURIComponent(q)}&top_k=${encodeURIComponent(topK.value)}`
    const controller = new AbortController()
    currentStreamController.value = controller
    const resp = await fetch(url, {
      method: 'GET',
      headers: {
        token,
      },
      signal: controller.signal,
    })
    if (!resp.ok || !resp.body) {
      assistant.thinking = false
      assistant.content = '流式请求失败，请稍后重试。'
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        const raw = line.slice(5).trim()
        if (!raw) continue
        try {
          const payload = JSON.parse(raw)
          if (payload.type === 'meta') {
            assistant.refs = payload.references || []
            persistSession()
          } else if (payload.type === 'delta') {
            assistant.thinking = false
            assistant.content += payload.content || ''
            persistSession()
            scrollToBottom()
          } else if (payload.type === 'done') {
            assistant.thinking = false
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  } finally {
    streamAsking.value = false
    currentStreamController.value = null
  }
}

function stopStreaming() {
  if (currentStreamController.value) {
    currentStreamController.value.abort()
    currentStreamController.value = null
  }
  streamAsking.value = false
}

restoreSession()
scrollToBottom()

onBeforeUnmount(() => {
  stopStreaming()
  persistSession()
})
</script>

<template>
  <CommonPage title="知识问答" show-footer>
    <NCard size="small" title="AI 对话" class="panel-card">
      <div ref="chatWindowRef" class="chat-window">
        <div v-if="!messages.length" class="placeholder">你好，我是 AI 知识库助手。请输入你的产品问题。</div>
        <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role === 'user' ? 'user' : 'assistant'">
          <NAvatar size="small">{{ msg.role === 'user' ? '我' : 'AI' }}</NAvatar>
          <div class="bubble">
            <div class="ts">{{ msg.ts }}</div>
            <div v-if="msg.role === 'assistant' && msg.thinking && !msg.content" class="thinking">正在思考中...</div>
            <div class="content">{{ msg.content }}</div>
            <div v-if="msg.role === 'assistant' && msg.refs?.length" class="refs">
              <NCollapse :default-expanded-names="refsCollapsed">
                <NCollapseItem title="参考来源" :name="`refs-${idx}`">
                  <div class="refs-list">
                    <NTag v-for="(r, i) in msg.refs" :key="i" type="info" size="small">{{ r.title }} ({{ r.score }})</NTag>
                  </div>
                </NCollapseItem>
              </NCollapse>
            </div>
            <div v-if="msg.role === 'assistant' && msg.content" class="answer-actions">
              <NButton size="tiny" tertiary @click="copyAnswer(msg.content)">复制答案</NButton>
            </div>
          </div>
        </div>
      </div>

      <div class="composer sticky-composer">
        <NInput v-model:value="question" type="textarea" :rows="3" placeholder="请输入产品功能问题，Enter发送，Shift+Enter换行" @keydown="onAskKeydown" />
        <NSpace align="center" justify="space-between" class="composer-actions">
          <NSpace align="center">
            <span>TopK</span>
            <NInputNumber v-model:value="topK" :min="1" :max="20" />
          </NSpace>
          <NSpace>
            <NButton :disabled="!canSubmit" :loading="asking" @click="ask">普通提问</NButton>
            <NButton type="primary" :disabled="!canSubmit" :loading="streamAsking" @click="askByStream">发送</NButton>
            <NButton v-if="streamAsking" type="warning" @click="stopStreaming">中断</NButton>
            <NButton tertiary @click="openFeedback">反馈评价</NButton>
            <NButton quaternary @click="clearSession">清空会话</NButton>
          </NSpace>
        </NSpace>
      </div>
    </NCard>

    <NCard v-if="feedbackVisible" size="small" title="回答评价" class="panel-card">
      <div style="display:flex; align-items:center; gap:10px;">
        <span>评分：</span>
        <NRate v-model:value="feedbackScore" :count="5" />
      </div>
      <NInput v-model:value="feedbackComment" type="textarea" :rows="3" placeholder="补充建议（可选）" style="margin-top:10px;" />
      <NSpace style="margin-top:10px;">
        <NButton type="primary" @click="submitFeedback">提交评价</NButton>
        <NButton @click="feedbackVisible = false">取消</NButton>
      </NSpace>
    </NCard>
  </CommonPage>
</template>

<style scoped>
.chat-window {
  min-height: 360px;
  max-height: 560px;
  overflow: auto;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 45%, #f9fafb 100%);
}

.placeholder {
  color: #6b7280;
  font-size: 13px;
  padding: 8px;
}

.msg-row {
  display: flex;
  gap: 8px;
  margin: 12px 0;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 14px;
  background: #eef2ff;
  box-shadow: 0 4px 12px rgba(30, 41, 59, 0.06);
}

.msg-row.assistant .bubble {
  background: #f3f4f6;
}

.content {
  white-space: pre-wrap;
  line-height: 1.6;
}

.ts {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 4px;
}

.thinking {
  color: #4b5563;
  font-size: 13px;
  margin-bottom: 4px;
}

.refs {
  margin-top: 8px;
}

.refs-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.answer-actions {
  margin-top: 8px;
}

.composer {
  margin-top: 12px;
}

.composer-actions {
  margin-top: 10px;
  width: 100%;
}

.panel-card {
  margin-top: 12px;
}

.sticky-composer {
  position: sticky;
  bottom: 0;
  padding-top: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.7), #fff);
  backdrop-filter: blur(2px);
}

@media (max-width: 900px) {
  .chat-window {
    min-height: 300px;
    max-height: 480px;
  }

  .bubble {
    max-width: 88%;
  }
}
</style>
