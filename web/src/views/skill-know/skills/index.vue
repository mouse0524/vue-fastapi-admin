<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '技能管理' })

const loading = ref(false)
const saving = ref(false)
const skills = ref([])
const selected = ref(null)
const keyword = ref('')
const filterType = ref('')
const showModal = ref(false)
const form = reactive({ id: null, name: '', description: '', category: 'prompt', content: '', trigger_keywords: '', priority: 100, is_active: true })

const filteredSkills = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return skills.value.filter((item) => {
    if (filterType.value && item.type !== filterType.value) return false
    if (!kw) return true
    return `${item.name} ${item.description} ${item.content}`.toLowerCase().includes(kw)
  })
})

onMounted(async () => {
  await api.skillKnowInitialize()
  await loadSkills()
})

async function loadSkills() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 100 }
    const res = await api.skillKnowSkills(params)
    skills.value = res.data || []
    if (!selected.value && skills.value.length) selected.value = skills.value[0]
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, { id: null, name: '', description: '', category: 'prompt', content: '', trigger_keywords: '', priority: 100, is_active: true })
  showModal.value = true
}

function openEdit() {
  if (!selected.value) return
  Object.assign(form, {
    id: selected.value.id,
    name: selected.value.name,
    description: selected.value.description,
    category: selected.value.category,
    content: selected.value.content,
    trigger_keywords: (selected.value.trigger_keywords || []).join(', '),
    priority: selected.value.priority,
    is_active: selected.value.is_active,
  })
  showModal.value = true
}

async function saveSkill() {
  saving.value = true
  const payload = {
    name: form.name,
    description: form.description,
    category: form.category,
    content: form.content,
    trigger_keywords: form.trigger_keywords.split(',').map((i) => i.trim()).filter(Boolean),
    priority: Number(form.priority) || 100,
    is_active: form.is_active,
  }
  try {
    if (form.id) {
      await api.skillKnowUpdateSkill({ skill_id: form.id, ...payload })
      $message.success('保存成功')
    } else {
      await api.skillKnowCreateSkill(payload)
      $message.success('创建成功')
    }
    showModal.value = false
    await loadSkills()
    if (form.id) selected.value = skills.value.find((item) => item.id === form.id) || selected.value
  } finally {
    saving.value = false
  }
}

async function deleteSkill() {
  if (!selected.value) return
  if (!selected.value.is_deletable) return $message.warning('系统技能不可删除')
  window.$dialog.warning({
    title: '确认删除',
    content: `确定删除技能「${selected.value.name}」吗？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await api.skillKnowDeleteSkill({ skill_id: selected.value.id })
      selected.value = null
      await loadSkills()
    },
  })
}

const typeLabels = { system: '系统', document: '文档', user: '用户' }
const categoryLabels = { search: '搜索', prompt: '提示词', retrieval: '检索', tool: '工具', workflow: '工作流' }
</script>

<template>
  <CommonPage title="技能管理" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">Skill 知识编排中心</h2>
      <p class="sk-hero-sub">统一管理系统技能、文档技能与用户技能，支持三层内容检索与对话增强。</p>
    </div>
    <div class="sk-shell">
      <NCard class="sk-sidebar" :bordered="false">
        <NSpace vertical size="medium">
          <div class="sk-toolbar-row">
            <NButton class="sk-btn" type="primary" @click="openCreate">新建 Skill</NButton>
            <NButton class="sk-btn" secondary :loading="loading" @click="loadSkills">刷新</NButton>
          </div>
          <NInput v-model:value="keyword" clearable placeholder="搜索技能名称、描述、内容" />
          <NRadioGroup v-model:value="filterType" size="small">
            <NRadioButton value="">全部</NRadioButton>
            <NRadioButton value="system">系统</NRadioButton>
            <NRadioButton value="document">文档</NRadioButton>
            <NRadioButton value="user">用户</NRadioButton>
          </NRadioGroup>
          <NSpin :show="loading">
            <div class="sk-list">
              <div
                v-for="item in filteredSkills"
                :key="item.id"
                class="sk-list-item"
                :class="{ active: selected?.id === item.id }"
                @click="selected = item"
              >
                <div class="item-title">{{ item.name }}</div>
                <div class="item-desc">{{ item.description }}</div>
                <NSpace size="small" class="item-tags">
                  <NTag size="small" :type="item.type === 'system' ? 'error' : item.type === 'document' ? 'info' : 'success'">
                    {{ typeLabels[item.type] }}
                  </NTag>
                  <NTag size="small">{{ categoryLabels[item.category] || item.category }}</NTag>
                </NSpace>
              </div>
              <NEmpty v-if="!filteredSkills.length" description="暂无技能" />
            </div>
          </NSpin>
        </NSpace>
      </NCard>

      <NCard class="sk-detail" :bordered="false">
        <template v-if="selected">
          <NSpace justify="space-between" align="start">
            <div>
              <h2>{{ selected.name }}</h2>
              <p class="muted">{{ selected.description }}</p>
            </div>
            <NSpace>
              <NButton secondary :disabled="!selected.is_editable" @click="openEdit">编辑</NButton>
              <NButton secondary type="error" :disabled="!selected.is_deletable" @click="deleteSkill">删除</NButton>
            </NSpace>
          </NSpace>
          <NGrid :cols="4" :x-gap="12" class="metric-grid">
            <NGi><NCard size="small"><div class="metric-label">类型</div><b>{{ typeLabels[selected.type] }}</b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">分类</div><b>{{ categoryLabels[selected.category] }}</b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">优先级</div><b>{{ selected.priority }}</b></NCard></NGi>
            <NGi><NCard size="small"><div class="metric-label">状态</div><b>{{ selected.is_active ? '启用' : '禁用' }}</b></NCard></NGi>
          </NGrid>
          <NCard size="small" title="L0 Abstract" class="section-card"><p>{{ selected.abstract || '-' }}</p></NCard>
          <NCard size="small" title="L1 Overview" class="section-card"><pre>{{ selected.overview || '-' }}</pre></NCard>
          <NCard size="small" title="L2 Content" class="section-card"><pre>{{ selected.content }}</pre></NCard>
        </template>
        <NEmpty v-else description="请选择一个技能" />
      </NCard>
    </div>
    </div>

    <NModal v-model:show="showModal" preset="card" :title="form.id ? '编辑 Skill' : '新建 Skill'" style="width: 720px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="form.name" /></NFormItem>
        <NFormItem label="描述"><NInput v-model:value="form.description" /></NFormItem>
        <NFormItem label="分类">
          <NSelect v-model:value="form.category" :options="Object.keys(categoryLabels).map((value) => ({ label: categoryLabels[value], value }))" />
        </NFormItem>
        <NFormItem label="触发关键词"><NInput v-model:value="form.trigger_keywords" placeholder="逗号分隔" /></NFormItem>
        <NFormItem label="内容"><NInput v-model:value="form.content" type="textarea" :autosize="{ minRows: 8, maxRows: 16 }" /></NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end"><NButton @click="showModal = false">取消</NButton><NButton type="primary" :loading="saving" @click="saveSkill">保存</NButton></NSpace>
      </template>
    </NModal>
  </CommonPage>
</template>

<style scoped>
.sk-shell { display: grid; grid-template-columns: 360px 1fr; gap: 16px; min-height: calc(100vh - 170px); }
.sk-sidebar, .sk-detail { border-radius: 18px; }
.sk-list { max-height: calc(100vh - 330px); overflow: auto; }
.sk-list-item { padding: 12px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; transition: .2s; }
.sk-list-item:hover, .sk-list-item.active { background: rgba(24, 160, 88, .08); border-color: rgba(24, 160, 88, .22); }
.item-title { font-weight: 700; }
.item-desc, .muted, .metric-label { color: #7b8494; font-size: 12px; }
.item-tags { margin-top: 8px; }
.metric-grid, .section-card { margin-top: 16px; }
pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
@media (max-width: 900px) { .sk-shell { grid-template-columns: 1fr; } }
</style>
