<script setup>
import { h, ref } from 'vue'
import { NButton, NInput, NInputNumber, NPopconfirm, NSpace, NUpload } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import api from '@/api'

defineOptions({ name: '文档中心' })

const tableRef = ref(null)
const queryItems = ref({ keyword: '', space_id: null })
const form = ref({ space_id: null, title: '', content: '' })
const uploading = ref(false)

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '空间ID', key: 'space_id', width: 100, align: 'center' },
  { title: '标题', key: 'title', align: 'left' },
  { title: '状态', key: 'parse_status', width: 100, align: 'center' },
  { title: '创建人ID', key: 'created_by', width: 100, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 180, align: 'center' },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    align: 'center',
    render(row) {
      return h(NSpace, { size: 'small', justify: 'center' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'warning',
              onClick: () => reparse(row.id),
            },
            { default: () => '重解析' }
          ),
          h(
            NPopconfirm,
            { onPositiveClick: () => removeDocument(row.id) },
            {
              trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
              default: () => '确认删除该文档？',
            }
          ),
        ],
      })
    },
  },
]

async function getData(params = {}) {
  const res = await api.kbDocumentList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

async function createDocument() {
  if (!form.value.space_id) {
    $message.warning('请输入空间ID')
    return
  }
  if (!form.value.title?.trim() || !form.value.content?.trim()) {
    $message.warning('请填写标题和正文')
    return
  }
  await api.kbDocumentCreate({
    space_id: Number(form.value.space_id),
    title: form.value.title.trim(),
    source_type: 'manual',
    source_url: null,
    content: form.value.content,
  })
  form.value = { space_id: form.value.space_id, title: '', content: '' }
  $message.success('文档创建成功')
  tableRef.value?.handleSearch()
}

async function uploadDocument(options) {
  if (!form.value.space_id) {
    $message.warning('请先输入空间ID')
    options.onError()
    return
  }
  try {
    uploading.value = true
    await api.kbDocumentUpload(Number(form.value.space_id), options.file.file, form.value.title || '')
    options.onFinish()
    $message.success('上传成功')
    tableRef.value?.handleSearch()
  } catch (error) {
    options.onError()
  } finally {
    uploading.value = false
  }
}

async function reparse(documentId) {
  await api.kbDocumentReparse({ document_id: documentId })
  $message.success('重解析已执行')
  tableRef.value?.handleSearch()
}

async function removeDocument(documentId) {
  await api.kbDocumentDelete({ id: documentId })
  $message.success('文档已删除')
  tableRef.value?.handleSearch()
}
</script>

<template>
  <CommonPage title="文档中心" show-footer>
    <NSpace vertical>
      <NSpace vertical style="width: 100%">
        <NSpace>
          <NInputNumber v-model:value="form.space_id" :min="1" placeholder="空间ID" style="width: 160px" />
          <NInput v-model:value="form.title" placeholder="文档标题" style="width: 260px" />
          <NButton type="primary" @click="createDocument">新增文档</NButton>
          <NUpload :default-upload="false" :custom-request="uploadDocument" :max="1">
            <NButton :loading="uploading">上传文件</NButton>
          </NUpload>
        </NSpace>
        <NInput
          v-model:value="form.content"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 8 }"
          placeholder="文档正文（MVP手动录入）"
        />
      </NSpace>

      <CrudTable ref="tableRef" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
        <template #queryBar>
          <QueryBarItem label="空间ID" :label-width="60">
            <NInputNumber v-model:value="queryItems.space_id" :min="1" placeholder="空间ID" />
          </QueryBarItem>
          <QueryBarItem label="关键字" :label-width="60">
            <NInput v-model:value="queryItems.keyword" clearable placeholder="标题关键字" />
          </QueryBarItem>
        </template>
      </CrudTable>
    </NSpace>
  </CommonPage>
</template>
