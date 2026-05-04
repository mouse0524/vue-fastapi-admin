<script setup>
import { onMounted, reactive, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '快速设置' })

const loading = ref(false)
const testing = ref(false)
const saving = ref(false)
const state = ref(null)
const form = reactive({ llm_api_key: '', llm_base_url: 'https://api.openai.com/v1', llm_chat_model: 'gpt-4o-mini', llm_embedding_model: 'text-embedding-3-small' })

onMounted(loadState)

async function loadState() {
  loading.value = true
  try {
    const res = await api.skillKnowSetupState()
    state.value = res.data
    Object.assign(form, {
      llm_base_url: res.data?.llm?.llm_base_url || form.llm_base_url,
      llm_chat_model: res.data?.llm?.llm_chat_model || form.llm_chat_model,
      llm_embedding_model: res.data?.llm?.llm_embedding_model || form.llm_embedding_model,
    })
  } finally {
    loading.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    const res = await api.skillKnowTestConnection(form)
    if (res.data?.success) $message.success(res.data.message || '连接成功')
    else $message.error(res.data?.message || '连接失败')
  } finally {
    testing.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      llm_base_url: form.llm_base_url,
      llm_chat_model: form.llm_chat_model,
      llm_embedding_model: form.llm_embedding_model,
    }
    if (form.llm_api_key && form.llm_api_key.trim()) payload.llm_api_key = form.llm_api_key.trim()
    const res = await api.skillKnowCompleteSetup(payload)
    state.value = res.data
    form.llm_api_key = ''
    $message.success('保存成功')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <CommonPage title="快速设置" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">模型与向量配置</h2>
      <p class="sk-hero-sub">配置 OpenAI 兼容模型、Embedding 与连接检测，驱动检索与对话能力。</p>
    </div>
    <NSpin :show="loading">
      <div class="setup-shell">
        <NCard :bordered="false" class="setup-card">
          <h2>OpenAI 兼容模型配置</h2>
          <p class="muted">用于内容分析、Embedding、语义检索和智能对话。不使用 LangGraph/Qdrant。</p>
          <NForm label-placement="top">
            <NFormItem label="API Key"><NInput v-model:value="form.llm_api_key" type="password" show-password-on="click" placeholder="sk-..." /></NFormItem>
            <div v-if="state?.llm?.llm_api_key" class="sk-muted" style="margin-top:-8px;margin-bottom:8px">
              已保存 Key（脱敏）：{{ state.llm.llm_api_key }}
            </div>
            <NFormItem label="Base URL"><NInput v-model:value="form.llm_base_url" /></NFormItem>
            <NFormItem label="Chat Model"><NInput v-model:value="form.llm_chat_model" /></NFormItem>
            <NFormItem label="Embedding Model"><NInput v-model:value="form.llm_embedding_model" /></NFormItem>
          </NForm>
          <NSpace><NButton secondary :loading="testing" @click="testConnection">测试连接</NButton><NButton type="primary" :loading="saving" @click="save">保存配置</NButton></NSpace>
        </NCard>
        <NCard :bordered="false" title="配置检查清单" class="setup-card">
          <NSpace vertical>
            <div v-for="item in state?.checklist || []" :key="item.key" class="check-item">
              <NTag :type="item.done ? 'success' : 'warning'">{{ item.done ? '完成' : '待配置' }}</NTag>
              <span>{{ item.label }}</span>
            </div>
          </NSpace>
          <NDivider />
          <NDescriptions :column="1" bordered size="small">
            <NDescriptionsItem label="状态">{{ state?.configured ? '已配置' : '未配置' }}</NDescriptionsItem>
            <NDescriptionsItem label="Base URL">{{ state?.llm?.llm_base_url }}</NDescriptionsItem>
            <NDescriptionsItem label="Chat Model">{{ state?.llm?.llm_chat_model }}</NDescriptionsItem>
            <NDescriptionsItem label="Embedding Model">{{ state?.llm?.llm_embedding_model }}</NDescriptionsItem>
            <NDescriptionsItem label="API Key">{{ state?.llm?.llm_api_key || '未配置' }}</NDescriptionsItem>
          </NDescriptions>
        </NCard>
      </div>
    </NSpin>
    </div>
  </CommonPage>
</template>

<style scoped>
.setup-shell { display: grid; grid-template-columns: 1.2fr .8fr; gap: 16px; }
.setup-card { border-radius: 20px; }
.muted { color: #7b8494; }
.check-item { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 12px; background: rgba(148, 163, 184, .08); }
@media (max-width: 900px) { .setup-shell { grid-template-columns: 1fr; } }
</style>
