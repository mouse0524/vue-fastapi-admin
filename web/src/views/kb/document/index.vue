<script setup>
import { h, ref } from 'vue'
import { NButton, NInput, NInputNumber, NPopconfirm, NSpace, NUpload } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import api from '@/api'

defineOptions({ name: '文档中心' })

const tableRef = ref(null)
const queryItems = ref({ keyword: '', space_id: null, parse_status: '', source_type: '' })
const form = ref({ space_id: null, title: '', content: '' })
const uploading = ref(false)
const processingPending = ref(false)

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '空间ID', key: 'space_id', width: 100, align: 'center' },
  { title: '标题', key: 'title', align: 'left' },
  { title: '类型', key: 'source_type', width: 90, align: 'center' },
  { title: '状态', key: 'parse_status', width: 100, align: 'center' },
  { title: '哈希', key: 'file_hash', width: 180, align: 'center', ellipsis: { tooltip: true } },
  { title: '解析信息', key: 'parse_error', width: 180, align: 'center', ellipsis: { tooltip: true } },
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
          row.parse_status === 'pending'
            ? h(
                NButton,
                {
                  size: 'small',
                  type: 'info',
                  quaternary: true,
                  onClick: () => processPending(row.id),
                },
                { default: () => '处理待解析' }
              )
            : null,
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
  const res = await api.kbDocumentCreate({
    space_id: Number(form.value.space_id),
    title: form.value.title.trim(),
    source_type: 'manual',
    source_url: null,
    content: form.value.content,
  })
  form.value = { space_id: form.value.space_id, title: '', content: '' }
  if (res?.data?.reused) {
    $message.info('检测到相同正文内容，已复用已有文档记录')
  } else {
    $message.success('文档创建成功')
  }
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
    const res = await api.kbDocumentUpload(Number(form.value.space_id), options.file.file, form.value.title || '')
    options.onFinish()
    if (res?.data?.reused) {
      $message.info('检测到重复文件，已复用已有文档记录')
    } else {
      $message.success('上传成功')
    }
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

async function processPending(documentId = null) {
  try {
    processingPending.value = true
    const res = await api.kbDocumentProcessPending(documentId ? { document_id: documentId } : {})
    const data = res?.data || {}
    $message.success(`处理完成：成功 ${data.success || 0} 条，失败 ${data.failed || 0} 条`)
    tableRef.value?.handleSearch()
  } finally {
    processingPending.value = false
  }
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
          <NButton type="warning" ghost :loading="processingPending" @click="processPending()">处理待解析</NButton>
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
          <QueryBarItem label="状态" :label-width="60">
            <NInput v-model:value="queryItems.parse_status" clearable placeholder="如 success / pending" />
          </QueryBarItem>
          <QueryBarItem label="类型" :label-width="60">
            <NInput v-model:value="queryItems.source_type" clearable placeholder="如 manual / upload" />
          </QueryBarItem>
        </template>
      </CrudTable>
    </NSpace>
  </CommonPage>
</template>
