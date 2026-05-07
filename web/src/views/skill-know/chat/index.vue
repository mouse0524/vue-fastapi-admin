<script setup>
import { nextTick, ref } from 'vue'
import { getToken } from '@/utils'
import CommonPage from '@/components/page/CommonPage.vue'

defineOptions({ name: '智能对话' })

const input = ref('')
const streaming = ref(false)
const timeline = ref([])
const answer = ref('')
const conversationId = ref(null)
const scroller = ref(null)
const collapsedTypes = ref(new Set())

function pushEvent(item) {
  timeline.value.push(item)
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

async function send() {
  if (!input.value.trim() || streaming.value) return
  const message = input.value.trim()
  input.value = ''
  answer.value = ''
  streaming.value = true
  pushEvent({ type: 'user.message', payload: { content: message } })
  try {
    const resp = await fetch(`${import.meta.env.VITE_BASE_API}/skill-know/chat/agent/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', token: getToken() || '' },
      body: JSON.stringify({ message, conversation_id: conversationId.value, use_tools: true }),
    })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.split('\n').find((i) => i.startsWith('data:'))
        if (!line) continue
        const item = JSON.parse(line.replace(/^data:\s*/, ''))
        if (item.type === 'assistant.delta') answer.value += item.payload?.content || ''
        else if (item.type === 'final') conversationId.value = item.payload?.conversation_id || conversationId.value
        else pushEvent(item)
      }
    }
  } catch (error) {
    pushEvent({ type: 'error', payload: { message: error.message || '对话失败' } })
  } finally {
    streaming.value = false
    if (answer.value) pushEvent({ type: 'assistant.message', payload: { content: answer.value } })
  }
}

function resetChat() {
  timeline.value = []
  answer.value = ''
  conversationId.value = null
}

function toggleType(type) {
  if (collapsedTypes.value.has(type)) collapsedTypes.value.delete(type)
  else collapsedTypes.value.add(type)
  collapsedTypes.value = new Set(collapsedTypes.value)
}

function isCollapsed(type) {
  return collapsedTypes.value.has(type)
}

function eventTitle(type) {
  return {
    'user.message': '用户消息',
    'phase.changed': '阶段切换',
    'support.match': '产品问题匹配',
    'search.results': '检索结果',
    'skill.activated': 'Skill 激活',
    'tools.registered': '工具注册',
    'llm.call.started': '模型调用',
    'llm.call.completed': '模型完成',
    'assistant.message': 'AI 回复',
    error: '错误',
  }[type] || type
}
</script>

<template>
  <CommonPage title="智能对话" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">Agent 时间线对话</h2>
      <p class="sk-hero-sub">实时展示检索、技能激活、模型调用与错误事件，支持可追踪的知识问答流程。</p>
    </div>
    <div class="chat-shell">
      <NCard class="timeline-card" :bordered="false">
        <template #header>
          <NSpace justify="space-between"><span>Skill-Know Agent 时间线</span><NButton secondary size="small" @click="resetChat">新对话</NButton></NSpace>
        </template>
        <div ref="scroller" class="timeline-scroll">
          <NEmpty v-if="!timeline.length" description="开始一次基于知识库的对话" />
            <div v-for="(item, idx) in timeline" :key="idx" class="event-card" :class="item.type.replaceAll('.', '-')">
              <NSpace justify="space-between" align="center">
                <b>{{ eventTitle(item.type) }}</b>
                <NSpace size="small">
                  <NTag size="small" style="cursor:pointer" @click="toggleType(item.type)">{{ isCollapsed(item.type) ? '展开' : '折叠' }}</NTag>
                  <NTag size="small">{{ item.type }}</NTag>
                </NSpace>
              </NSpace>
            <template v-if="!isCollapsed(item.type)">
            <div v-if="item.type === 'search.results'" class="event-body">
              <div v-for="skill in item.payload.items" :key="skill.chunk_uri || skill.id" class="skill-hit">
                <b>{{ skill.name || skill.title }}</b><span>{{ skill.source_type || 'skill' }} · score {{ skill.score || 0 }}</span>
                <div v-if="skill.heading" class="match-reasons">{{ skill.heading }}</div>
              </div>
            </div>
            <div v-else-if="item.type === 'support.match'" class="event-body">
              <p class="match-summary">分类：{{ item.payload.classification?.issue_category || '-' }}，置信度：{{ item.payload.confidence || 0 }}</p>
              <div v-for="skill in item.payload.items" :key="skill.id" class="skill-hit">
                <b>{{ skill.name }}</b><span> score {{ skill.score || 0 }}</span>
                <div v-if="skill.matched_reasons?.length" class="match-reasons">{{ skill.matched_reasons.join(' / ') }}</div>
                <div v-for="level in skill.solution_levels" :key="`${skill.id}-${level.level}`" class="solution-level">
                  <b>L{{ level.level }} {{ level.title }}</b>
                  <p>{{ (level.steps || []).join('；') }}</p>
                </div>
              </div>
              <div v-if="item.payload.clarifying_questions?.length" class="clarify-box">建议补充：{{ item.payload.clarifying_questions.join('；') }}</div>
            </div>
            <div v-else-if="item.type === 'assistant.message'" class="answer-body">{{ item.payload.content }}</div>
            <pre v-else>{{ JSON.stringify(item.payload, null, 2) }}</pre>
            </template>
            </div>
          <div v-if="streaming && answer" class="event-card assistant-message"><b>AI 回复中</b><div class="answer-body">{{ answer }}</div></div>
        </div>
        <div class="input-bar">
          <NInput v-model:value="input" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" placeholder="输入问题，支持 Markdown" @keydown.ctrl.enter="send" />
          <NButton type="primary" size="large" :loading="streaming" :disabled="!input.trim()" @click="send">发送</NButton>
        </div>
      </NCard>
    </div>
    </div>
  </CommonPage>
</template>

<style scoped>
.chat-shell { min-height: calc(100vh - 170px); }
.timeline-card { border-radius: 20px; height: calc(100vh - 170px); display: flex; flex-direction: column; }
.timeline-scroll { height: calc(100vh - 330px); overflow: auto; padding-right: 8px; }
.event-card { padding: 14px; border-radius: 14px; margin-bottom: 12px; background: rgba(148, 163, 184, .10); border: 1px solid rgba(148, 163, 184, .18); }
.skill-activated { background: rgba(139, 92, 246, .12); }
.search-results { background: rgba(32, 128, 240, .10); }
.phase-changed { background: rgba(245, 158, 11, .10); }
.tools-registered { background: rgba(14, 116, 144, .10); }
.llm-call-started, .llm-call-completed { background: rgba(30, 64, 175, .10); }
.assistant-message { background: rgba(24, 160, 88, .10); }
.error { background: rgba(208, 48, 80, .12); }
pre { margin: 8px 0 0; white-space: pre-wrap; font-size: 12px; }
.answer-body { white-space: pre-wrap; line-height: 1.7; margin-top: 8px; }
.skill-hit { padding: 8px 0; border-bottom: 1px dashed rgba(148, 163, 184, .3); }
.skill-hit span { color: #7b8494; margin-left: 8px; }
.match-summary, .match-reasons, .solution-level p, .clarify-box { color: #64748b; margin: 6px 0; }
.solution-level { margin-top: 8px; padding: 8px; border-radius: 10px; background: rgba(255,255,255,.55); }
.clarify-box { padding: 8px; border-radius: 10px; background: rgba(245, 158, 11, .10); }
.input-bar { display: grid; grid-template-columns: 1fr 110px; gap: 12px; margin-top: 16px; }
</style>
