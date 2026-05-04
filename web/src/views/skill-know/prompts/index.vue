<script setup>
import { onMounted, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '提示词管理' })

const loading = ref(false)
const saving = ref(false)
const prompts = ref([])
const selected = ref(null)

onMounted(loadPrompts)

async function loadPrompts() {
  loading.value = true
  try {
    const res = await api.skillKnowPrompts({ include_inactive: true })
    prompts.value = res.data?.items || []
    if (!selected.value && prompts.value.length) selected.value = prompts.value[0]
  } finally {
    loading.value = false
  }
}

async function savePrompt() {
  if (!selected.value) return
  saving.value = true
  try {
    await api.skillKnowUpdatePrompt(selected.value.key, { content: selected.value.content, is_active: selected.value.is_active })
    $message.success('保存成功')
    await loadPrompts()
  } finally {
    saving.value = false
  }
}

async function resetPrompt() {
  if (!selected.value) return
  const res = await api.skillKnowResetPrompt(selected.value.key)
  selected.value = res.data
  $message.success('已重置默认提示词')
}
</script>

<template>
  <CommonPage title="提示词管理" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">提示词中控台</h2>
      <p class="sk-hero-sub">管理系统提示词与变量模板，保障检索、生成、对话输出的一致性。</p>
    </div>
    <div class="prompt-shell">
      <NCard :bordered="false" class="prompt-list">
        <NSpin :show="loading">
          <div v-for="item in prompts" :key="item.key" class="prompt-item" :class="{ active: selected?.key === item.key }" @click="selected = item">
            <b>{{ item.name }}</b>
            <p>{{ item.description }}</p>
            <NTag size="small">{{ item.category }}</NTag>
          </div>
        </NSpin>
      </NCard>
      <NCard :bordered="false" class="prompt-editor">
        <template v-if="selected">
          <NSpace justify="space-between" align="center">
            <div><h2>{{ selected.name }}</h2><p>{{ selected.key }}</p></div>
            <NSpace><NSwitch v-model:value="selected.is_active" /><NButton secondary @click="resetPrompt">重置</NButton><NButton type="primary" :loading="saving" @click="savePrompt">保存</NButton></NSpace>
          </NSpace>
          <NCard size="small" title="变量" class="section-card"><NTag v-for="item in selected.variables" :key="item" size="small" class="var-tag">{{ item }}</NTag></NCard>
          <NInput v-model:value="selected.content" type="textarea" :autosize="{ minRows: 18, maxRows: 32 }" />
        </template>
        <NEmpty v-else description="请选择提示词" />
      </NCard>
    </div>
    </div>
  </CommonPage>
</template>

<style scoped>
.prompt-shell { display: grid; grid-template-columns: 340px 1fr; gap: 16px; min-height: calc(100vh - 170px); }
.prompt-item { padding: 14px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; }
.prompt-item:hover, .prompt-item.active { background: rgba(139, 92, 246, .10); border-color: rgba(139, 92, 246, .22); }
.prompt-item p { color: #7b8494; font-size: 12px; }
.section-card { margin: 16px 0; }
.var-tag { margin-right: 8px; }
@media (max-width: 900px) { .prompt-shell { grid-template-columns: 1fr; } }
</style>
