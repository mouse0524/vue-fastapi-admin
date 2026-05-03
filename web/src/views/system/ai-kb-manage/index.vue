<script setup>
import { ref } from 'vue'
import { NButton, NCard, NInputNumber, NList, NListItem, NPopconfirm, NUpload } from 'naive-ui'
import { useUserStore } from '@/store'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '知识管理' })
const userStore = useUserStore()

const docs = ref([])
const docsLoading = ref(false)
const reindexLoading = ref(false)
const reindexIncremental = ref(true)
const confLoading = ref(false)
const saveConfLoading = ref(false)
const statusLoading = ref(false)
const historyLoading = ref(false)
const rebuildHistory = ref([])

const aiConfig = ref({
  ai_kb_enabled: true,
  ai_kb_top_k: 5,
  ai_kb_chunk_size: 800,
  ai_kb_chunk_overlap: 120,
  ai_kb_max_upload_size: 20 * 1024 * 1024,
  ai_kb_feedback_window: 20,
  ai_kb_auto_reindex_threshold: 5,
  ai_kb_openai_base_url: '',
  ai_kb_openai_api_key: '',
  ai_kb_openai_model: 'gpt-4o-mini',
  ai_kb_embedding_model: 'text-embedding-3-small',
  ai_kb_llm_timeout_seconds: 20,
})

const statusData = ref({
  doc_count: 0,
  chunk_count: 0,
  recent_feedback: 0,
  recent_low_score: 0,
  last_evolution: '',
  last_rebuild: '',
  skill_prompt_loaded: false,
  skill_prompt_dir: '',
})

function parseLastRebuildMs(line) {
  const m = String(line || '').match(/took_ms=(\d+)/)
  return m ? Number(m[1]) : 0
}

async function loadDocs() {
  docsLoading.value = true
  try {
    const res = await api.aiKbDocs({ page: 1, page_size: 50 })
    docs.value = res?.data || []
  } finally {
    docsLoading.value = false
  }
}

async function rebuildIndex() {
  reindexLoading.value = true
  try {
    const res = await api.aiKbReindex({ incremental: reindexIncremental.value })
    const data = res?.data || {}
    $message.success(
      `索引重建完成 mode=${data.mode || '-'} chunks=${data.chunks || 0} changed=${data.changed_files || 0} removed=${data.removed_files || 0}`
    )
    await loadStatus()
  } finally {
    reindexLoading.value = false
  }
}

async function loadAiConfig() {
  confLoading.value = true
  try {
    const res = await api.aiKbGetConfig()
    aiConfig.value = { ...aiConfig.value, ...(res?.data || {}) }
  } finally {
    confLoading.value = false
  }
}

async function saveAiConfig() {
  saveConfLoading.value = true
  try {
    await api.aiKbUpdateConfig(aiConfig.value)
    $message.success('AI知识库配置已保存')
  } finally {
    saveConfLoading.value = false
  }
}

async function loadStatus() {
  statusLoading.value = true
  try {
    const res = await api.aiKbStatus()
    statusData.value = { ...statusData.value, ...(res?.data || {}) }
  } finally {
    statusLoading.value = false
  }
}

async function loadRebuildHistory() {
  historyLoading.value = true
  try {
    const res = await api.aiKbRebuildHistory({ limit: 50 })
    rebuildHistory.value = res?.data || []
  } finally {
    historyLoading.value = false
  }
}

async function handleUpload({ file }) {
  await api.aiKbUpload(file.file)
  $message.success('文档上传成功')
  await loadDocs()
}

async function deleteDoc(name) {
  await api.aiKbDeleteDoc({ name })
  $message.success('文档已删除')
  await loadDocs()
}

async function reindexOneDoc(name) {
  const res = await api.aiKbReindexOne({ name })
  const data = res?.data || {}
  $message.success(`单文档重建完成 doc_chunks=${data.doc_chunks || 0} chunks=${data.chunks || 0}`)
  await loadStatus()
  await loadRebuildHistory()
}

loadDocs()
loadAiConfig()
loadStatus()
loadRebuildHistory()
</script>

<template>
  <CommonPage title="知识管理" show-footer>
    <NCard v-if="!userStore.isSuperUser" size="small" style="margin-bottom:12px;">
      <div style="color:#b45309;">当前页面为管理员专属操作区，建议仅管理员访问。</div>
    </NCard>

    <NCard size="small" class="panel-card">
      <div class="summary-grid">
        <div class="summary-item">
          <div class="summary-label">文档数</div>
          <div class="summary-value">{{ statusData.doc_count }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">分片数</div>
          <div class="summary-value">{{ statusData.chunk_count }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">最近重建耗时</div>
          <div class="summary-value">{{ parseLastRebuildMs(statusData.last_rebuild) || 0 }} ms</div>
        </div>
      </div>
    </NCard>

    <NCard title="学习文档" size="small" class="panel-card">
      <NUpload :custom-request="handleUpload" :show-file-list="false">
        <NButton>上传文档（pdf/doc/docx/md/txt）</NButton>
      </NUpload>
      <NButton style="margin-left:12px;" :loading="docsLoading" @click="loadDocs">刷新列表</NButton>
      <NButton style="margin-left:12px;" :loading="reindexLoading" @click="rebuildIndex">重建索引</NButton>
      <NButton style="margin-left:12px;" @click="reindexIncremental = !reindexIncremental">
        {{ reindexIncremental ? '当前：增量重建' : '当前：全量重建' }}
      </NButton>
      <NList class="doc-list">
        <NListItem v-for="item in docs" :key="item.name">
          <div style="display:flex; justify-content:space-between; gap:12px; width:100%; align-items:center;">
            <span>{{ item.name }} - {{ item.size }} bytes - {{ item.updated_at }}</span>
            <div style="display:flex; gap:8px;">
              <NButton size="small" type="primary" tertiary @click="reindexOneDoc(item.name)">单文档重建</NButton>
              <NPopconfirm @positive-click="deleteDoc(item.name)">
                <template #trigger>
                  <NButton size="small" type="error" tertiary>删除</NButton>
                </template>
                确认删除该文档？
              </NPopconfirm>
            </div>
          </div>
        </NListItem>
      </NList>
    </NCard>

    <NCard title="运行配置" size="small" class="panel-card">
      <div class="config-grid">
        <div><div>OpenAI Base URL</div><input v-model="aiConfig.ai_kb_openai_base_url" class="plain-input" /></div>
        <div><div>OpenAI API Key</div><input v-model="aiConfig.ai_kb_openai_api_key" type="password" class="plain-input" /></div>
        <div><div>Chat Model</div><input v-model="aiConfig.ai_kb_openai_model" class="plain-input" /></div>
        <div><div>Embedding Model</div><input v-model="aiConfig.ai_kb_embedding_model" class="plain-input" /></div>
        <div><div>LLM超时(秒)</div><NInputNumber v-model:value="aiConfig.ai_kb_llm_timeout_seconds" :min="1" :max="120" /></div>
        <div><div>默认TopK</div><NInputNumber v-model:value="aiConfig.ai_kb_top_k" :min="1" :max="20" /></div>
        <div><div>切片长度</div><NInputNumber v-model:value="aiConfig.ai_kb_chunk_size" :min="100" :max="8000" /></div>
        <div><div>切片重叠</div><NInputNumber v-model:value="aiConfig.ai_kb_chunk_overlap" :min="1" :max="2000" /></div>
        <div><div>上传大小上限(byte)</div><NInputNumber v-model:value="aiConfig.ai_kb_max_upload_size" :min="1048576" :max="524288000" /></div>
        <div><div>低分反馈窗口</div><NInputNumber v-model:value="aiConfig.ai_kb_feedback_window" :min="1" :max="200" /></div>
        <div><div>自动重建阈值</div><NInputNumber v-model:value="aiConfig.ai_kb_auto_reindex_threshold" :min="1" :max="100" /></div>
      </div>
      <div style="margin-top:12px;">
        <NButton :loading="confLoading" @click="loadAiConfig">刷新配置</NButton>
        <NButton type="primary" style="margin-left:12px;" :loading="saveConfLoading" @click="saveAiConfig">保存配置</NButton>
      </div>
    </NCard>

    <NCard title="运行状态" size="small" class="panel-card">
      <div class="status-grid">
        <div>文档数量：{{ statusData.doc_count }}</div>
        <div>索引分片：{{ statusData.chunk_count }}</div>
        <div>近期反馈数：{{ statusData.recent_feedback }}</div>
        <div>近期低分数：{{ statusData.recent_low_score }}</div>
        <div>Skill提示词已加载：{{ statusData.skill_prompt_loaded ? '是' : '否' }}</div>
        <div>Skill目录：{{ statusData.skill_prompt_dir || '-' }}</div>
      </div>
      <div style="margin-top:8px; white-space:pre-wrap;">最近一次进化：{{ statusData.last_evolution || '暂无' }}</div>
      <div style="margin-top:8px; white-space:pre-wrap;">最近一次重建：{{ statusData.last_rebuild || '暂无' }}</div>
      <div style="margin-top:12px;"><NButton :loading="statusLoading" @click="loadStatus">刷新状态</NButton></div>
    </NCard>

    <NCard title="重建历史" size="small" class="panel-card">
      <NButton :loading="historyLoading" @click="loadRebuildHistory">刷新历史</NButton>
      <NList style="margin-top:12px; max-height:260px; overflow:auto;">
        <NListItem v-for="(line, idx) in rebuildHistory" :key="idx">{{ line }}</NListItem>
      </NList>
    </NCard>
  </CommonPage>
</template>

<style scoped>
.panel-card {
  margin-top: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 12px;
}

.summary-item {
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, #eff6ff, #f8fafc);
  border-radius: 10px;
  padding: 10px 12px;
}

.summary-label {
  color: #64748b;
  font-size: 12px;
}

.summary-value {
  color: #0f172a;
  font-weight: 700;
  font-size: 18px;
  margin-top: 2px;
}

.doc-list {
  margin-top: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 6px;
  background: linear-gradient(180deg, #f8fafc, #ffffff);
}

.config-grid,
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 12px;
}

.plain-input {
  width: 100%;
  height: 34px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 0 10px;
  box-sizing: border-box;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .config-grid,
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
