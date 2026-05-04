<script setup>
import { ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '知识包管理' })

const exporting = ref(false)
const importing = ref(false)
const category = ref('')
const folderId = ref('')
const skipDuplicates = ref(true)
const fileInput = ref(null)
const importResult = ref(null)

async function exportPack() {
  exporting.value = true
  try {
    const params = {}
    if (category.value.trim()) params.category = category.value.trim()
    if (folderId.value.trim()) params.folder_id = folderId.value.trim()
    const res = await api.skillKnowExportPack(params)
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `skill-know-pack-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    $message.success('导出成功')
  } finally {
    exporting.value = false
  }
}

async function importPack(e) {
  const file = e.target.files?.[0]
  if (!file) return
  importing.value = true
  try {
    const res = await api.skillKnowImportPack(file, { skip_duplicates: skipDuplicates.value })
    importResult.value = res.data
    $message.success('导入成功')
  } finally {
    importing.value = false
    e.target.value = ''
  }
}
</script>

<template>
  <CommonPage title="知识包管理" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">知识包导入导出</h2>
      <p class="sk-hero-sub">按分类/文件夹导出可复用知识包，支持跨环境导入并保留关系映射。</p>
    </div>
    <input ref="fileInput" type="file" class="hidden" accept="application/json" @change="importPack" />
    <NGrid :cols="2" :x-gap="16">
      <NGi>
        <NCard :bordered="false" title="导出知识包" class="pack-card">
          <NForm label-placement="top">
            <NFormItem label="分类（可选）"><NInput v-model:value="category" placeholder="search/prompt/retrieval" /></NFormItem>
            <NFormItem label="文件夹ID（可选）"><NInput v-model:value="folderId" placeholder="数字ID" /></NFormItem>
          </NForm>
          <NButton type="primary" :loading="exporting" @click="exportPack">导出 JSON</NButton>
        </NCard>
      </NGi>
      <NGi>
        <NCard :bordered="false" title="导入知识包" class="pack-card">
          <NCheckbox v-model:checked="skipDuplicates">跳过重复 Skill</NCheckbox>
          <div style="margin-top: 12px">
            <NButton type="primary" secondary :loading="importing" @click="fileInput?.click()">选择并导入 JSON</NButton>
          </div>
          <NAlert v-if="importResult" type="success" style="margin-top: 16px" :show-icon="false">
            导入结果：成功 {{ importResult.imported || 0 }}，跳过 {{ importResult.skipped || 0 }}，关系 {{ importResult.relations_imported || 0 }}
          </NAlert>
        </NCard>
      </NGi>
    </NGrid>
    </div>
  </CommonPage>
</template>

<style scoped>
.hidden { display: none; }
.pack-card { border-radius: 18px; min-height: 260px; }
</style>
