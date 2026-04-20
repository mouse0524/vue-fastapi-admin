<script setup>
import { h, ref } from 'vue'
import { NButton, NInput, NInputNumber, NModal, NSpace, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import api from '@/api'

defineOptions({ name: '模型日志' })

const tableRef = ref(null)
const queryItems = ref({ provider: '', model_code: '', error_code: '', session_id: null })
const testResult = ref(null)
const testing = ref(false)
const detailVisible = ref(false)
const detailTitle = ref('')
const detailContent = ref('')

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: 'Provider', key: 'provider', width: 120, align: 'center' },
  { title: 'Model', key: 'model_code', width: 140, align: 'center' },
  { title: '会话ID', key: 'session_id', width: 90, align: 'center' },
  { title: '输入Token', key: 'prompt_tokens', width: 100, align: 'center' },
  { title: '输出Token', key: 'completion_tokens', width: 100, align: 'center' },
  { title: '耗时(ms)', key: 'latency_ms', width: 90, align: 'center' },
  { title: '错误码', key: 'error_code', width: 120, align: 'center' },
  {
    title: '详情',
    key: 'detail',
    width: 120,
    align: 'center',
    render(row) {
      return h(NSpace, { size: 'small', justify: 'center' }, {
        default: () => [
          h(
            NButton,
            {
              text: true,
              type: 'primary',
              size: 'small',
              onClick: () => showDetail('Request', row.request_json),
            },
            { default: () => 'Request' }
          ),
          h(
            NButton,
            {
              text: true,
              type: 'info',
              size: 'small',
              onClick: () => showDetail('Response', row.response_json),
            },
            { default: () => 'Response' }
          ),
        ],
      })
    },
  },
  { title: '时间', key: 'created_at', width: 180, align: 'center' },
]

async function getData(params = {}) {
  const res = await api.kbLlmLogList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

async function testConnectivity() {
  try {
    testing.value = true
    const res = await api.kbLlmTest()
    testResult.value = res?.data || null
    if (testResult.value?.ok) {
      $message.success('模型连通性测试成功')
    } else {
      $message.warning('模型连通性测试失败，请检查配置')
    }
    tableRef.value?.handleSearch()
  } finally {
    testing.value = false
  }
}

function showDetail(type, data) {
  detailTitle.value = `${type} 详情`
  try {
    detailContent.value = data == null ? '无数据' : JSON.stringify(data, null, 2)
  } catch (error) {
    detailContent.value = String(data ?? '无数据')
  }
  detailVisible.value = true
}
</script>

<template>
  <CommonPage title="模型日志" show-footer>
    <NSpace vertical>
      <NSpace align="center">
        <NButton type="primary" :loading="testing" @click="testConnectivity">模型连通性测试</NButton>
        <template v-if="testResult">
          <NTag :type="testResult.ok ? 'success' : 'error'" :bordered="false">
            {{ testResult.ok ? '可用' : '不可用' }}
          </NTag>
          <span>provider: {{ testResult.provider || '-' }}</span>
          <span>model: {{ testResult.model || '-' }}</span>
          <span>latency: {{ testResult.latency_ms ?? '-' }}ms</span>
        </template>
      </NSpace>

      <CrudTable ref="tableRef" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
        <template #queryBar>
          <QueryBarItem label="Provider" :label-width="70">
            <NInput v-model:value="queryItems.provider" clearable placeholder="provider" />
          </QueryBarItem>
          <QueryBarItem label="Model" :label-width="60">
            <NInput v-model:value="queryItems.model_code" clearable placeholder="model" />
          </QueryBarItem>
          <QueryBarItem label="错误码" :label-width="60">
            <NInput v-model:value="queryItems.error_code" clearable placeholder="error_code" />
          </QueryBarItem>
          <QueryBarItem label="会话ID" :label-width="60">
            <NInputNumber v-model:value="queryItems.session_id" :min="1" placeholder="session_id" />
          </QueryBarItem>
        </template>
      </CrudTable>

      <NModal v-model:show="detailVisible" preset="card" style="width: 720px" :title="detailTitle">
        <pre style="max-height: 500px; overflow: auto; white-space: pre-wrap">{{ detailContent }}</pre>
      </NModal>
    </NSpace>
  </CommonPage>
</template>
