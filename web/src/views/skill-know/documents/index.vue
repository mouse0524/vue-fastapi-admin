<script setup>
import { computed, onMounted, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '文档管理' })

const loading = ref(false)
const uploading = ref(false)
const converting = ref(false)
const documents = ref([])
const folders = ref([])
const selected = ref(null)
const currentFolderId = ref(null)
const keyword = ref('')
const fileInput = ref(null)
const packInput = ref(null)
const batchFiles = ref([])
const batchTask = ref(null)

const filteredDocuments = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return documents.value
  return documents.value.filter((item) => `${item.title} ${item.filename} ${item.content}`.toLowerCase().includes(kw))
})

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  try {
    const folderParams = {}
    if (currentFolderId.value != null) folderParams.parent_id = currentFolderId.value
    const documentParams = { page: 1, page_size: 100 }
    if (currentFolderId.value != null) documentParams.folder_id = currentFolderId.value
    const [folderRes, docRes] = await Promise.all([
      api.skillKnowFolders(folderParams),
      api.skillKnowDocuments(documentParams),
    ])
    folders.value = folderRes.data || []
    documents.value = docRes.data || []
    if (!selected.value && documents.value.length) selected.value = documents.value[0]
  } finally {
    loading.value = false
  }
}

async function uploadFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await api.skillKnowUploadDocument(file, { folder_id: currentFolderId.value })
    selected.value = res.data
    $message.success('上传并解析完成')
    await loadAll()
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function runBatchUpload() {
  if (!batchFiles.value.length) return
  const res = await api.skillKnowBatchUpload(batchFiles.value, { folder_id: currentFolderId.value, use_llm: true })
  batchTask.value = res.data
  if (batchTask.value?.task_id) {
    const status = await api.skillKnowUploadTask({ task_id: batchTask.value.task_id })
    batchTask.value.status = status.data
  }
  await loadAll()
}

async function exportPack() {
  const params = {}
  if (currentFolderId.value != null) params.folder_id = currentFolderId.value
  const res = await api.skillKnowExportPack(params)
  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `skill-know-pack-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function importPack(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await api.skillKnowImportPack(file, { skip_duplicates: true })
  $message.success('知识包导入成功')
  await loadAll()
  e.target.value = ''
}

async function convertDocument() {
  if (!selected.value) return
  converting.value = true
  try {
    const res = await api.skillKnowConvertDocument({ document_id: selected.value.id, use_llm: true, auto_activate: true })
    $message.success(`已转换为 Skill：${res.data?.skill?.name || selected.value.title}`)
    await loadAll()
  } finally {
    converting.value = false
  }
}

async function deleteDocument() {
  if (!selected.value) return
  window.$dialog.warning({
    title: '确认删除',
    content: `确定删除文档「${selected.value.title}」吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await api.skillKnowDeleteDocument({ document_id: selected.value.id })
      selected.value = null
      await loadAll()
    },
  })
}

function statusText(status) {
  return { pending: '待处理', processing: '处理中', completed: '已完成', failed: '失败' }[status] || status
}
</script>

<template>
  <CommonPage title="文档管理" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">文档入库与 Skill 转化</h2>
      <p class="sk-hero-sub">上传文件后自动转换为 Markdown，生成分块并建立向量检索索引，可一键沉淀为 Skill。</p>
    </div>
    <div class="doc-shell">
      <NCard class="doc-sidebar" :bordered="false">
        <NSpace vertical>
          <input ref="fileInput" type="file" class="hidden" accept=".pdf,.pptx,.docx,.xlsx,.html,.htm,.csv,.json,.xml,.txt,.md,.markdown" @change="uploadFile" />
          <div class="sk-toolbar-row">
            <NButton class="sk-btn" type="primary" :loading="uploading" @click="fileInput?.click()">上传文档</NButton>
            <NButton class="sk-btn" secondary :loading="loading" @click="loadAll">刷新</NButton>
          </div>
          <div class="sk-toolbar-row">
            <NUpload multiple :default-upload="false" :show-file-list="true" @change="({ fileList }) => { batchFiles = fileList.map(i => i.file).filter(Boolean) }">
              <NButton class="sk-btn" tertiary>选择批量文件</NButton>
            </NUpload>
            <NButton class="sk-btn" secondary @click="runBatchUpload">批量上传</NButton>
          </div>
          <input ref="packInput" type="file" class="hidden" accept="application/json" @change="importPack" />
          <div class="sk-toolbar-row">
            <NButton class="sk-btn" quaternary @click="exportPack">导出知识包</NButton>
            <NButton class="sk-btn" quaternary @click="packInput?.click()">导入知识包</NButton>
          </div>
          <NAlert v-if="batchTask?.status" type="info" :show-icon="false">
            批量任务：{{ batchTask.status.status }}，总数 {{ batchTask.status.total }}，成功 {{ batchTask.status.completed }}，失败 {{ batchTask.status.failed }}
          </NAlert>
          <NInput v-model:value="keyword" clearable placeholder="搜索文档" />
          <NSpin :show="loading">
            <div class="doc-list">
              <div v-for="folder in folders" :key="`f-${folder.id}`" class="doc-list-item folder" @click="currentFolderId = folder.id; loadAll()">
                <div class="item-title">📁 {{ folder.name }}</div>
                <div class="item-desc">{{ folder.description || '文件夹' }}</div>
              </div>
              <div
                v-for="item in filteredDocuments"
                :key="item.id"
                class="doc-list-item"
                :class="{ active: selected?.id === item.id }"
                @click="selected = item"
              >
                <div class="item-title">📄 {{ item.title }}</div>
                <div class="item-desc">
                  {{ item.file_type?.toUpperCase() }}
                  <span v-if="item.extra_metadata?.original_file_type"> · 原始 {{ item.extra_metadata.original_file_type.toUpperCase() }}</span>
                  · {{ Math.max(1, item.file_size / 1024).toFixed(1) }} KB
                </div>
                <NSpace size="small" class="item-tags">
                  <span class="sk-status" :class="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'error' : 'warning'">{{ statusText(item.status) }}</span>
                  <NTag v-if="item.is_converted" size="small" type="info">已转 Skill</NTag>
                </NSpace>
              </div>
              <NEmpty v-if="!folders.length && !filteredDocuments.length" description="暂无文档" />
            </div>
          </NSpin>
        </NSpace>
      </NCard>
      <NCard class="doc-detail" :bordered="false">
        <template v-if="selected">
          <NSpace justify="space-between" align="start">
            <div><h2>{{ selected.title }}</h2><p class="muted">{{ selected.description || selected.filename }}</p></div>
            <NSpace>
              <NButton type="primary" :loading="converting" :disabled="selected.is_converted" @click="convertDocument">转为 Skill</NButton>
              <NButton secondary type="error" @click="deleteDocument">删除</NButton>
            </NSpace>
          </NSpace>
          <NGrid :cols="4" :x-gap="12" class="metric-grid">
            <NGi><NCard size="small"><div class="metric-label">状态</div><b>{{ statusText(selected.status) }}</b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">类型</div><b>{{ selected.file_type }}<span v-if="selected.extra_metadata?.original_file_type"> / {{ selected.extra_metadata.original_file_type }}</span></b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">分类</div><b>{{ selected.category || '-' }}</b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">索引</div><b>{{ selected.extra_metadata?.index_status || '-' }}<span v-if="selected.extra_metadata?.chunk_count"> / {{ selected.extra_metadata.chunk_count }} 块</span></b></NCard></NGi>
          </NGrid>
          <NCard size="small" title="L0 Abstract" class="section-card">{{ selected.abstract || '-' }}</NCard>
          <NCard size="small" title="L1 Overview" class="section-card"><pre>{{ selected.overview || '-' }}</pre></NCard>
          <NCard size="small" title="Markdown Content" class="section-card"><pre>{{ selected.content || selected.error_message || '-' }}</pre></NCard>
        </template>
        <NEmpty v-else description="请选择文档" />
      </NCard>
    </div>
    </div>
  </CommonPage>
</template>

<style scoped>
.hidden { display: none; }
.doc-shell { display: grid; grid-template-columns: 380px 1fr; gap: 16px; min-height: calc(100vh - 170px); }
.doc-list { max-height: calc(100vh - 300px); overflow: auto; }
.doc-list-item { padding: 12px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; transition: .2s; }
.doc-list-item:hover, .doc-list-item.active { background: rgba(32, 128, 240, .08); border-color: rgba(32, 128, 240, .22); }
.doc-list-item.folder { background: rgba(250, 173, 20, .08); }
.item-title { font-weight: 700; }
.item-desc, .muted, .metric-label { color: #7b8494; font-size: 12px; }
.item-tags, .metric-grid, .section-card { margin-top: 12px; }
pre { white-space: pre-wrap; word-break: break-word; margin: 0; max-height: 420px; overflow: auto; }
@media (max-width: 900px) { .doc-shell { grid-template-columns: 1fr; } }
</style>
