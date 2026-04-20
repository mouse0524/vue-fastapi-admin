<script setup>
import { ref } from 'vue'
import { NInput, NSelect } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import api from '@/api'

defineOptions({ name: '反馈标注' })

const tableRef = ref(null)
const queryItems = ref({ status: null })

const statusOptions = [
  { label: 'new', value: 'new' },
  { label: 'processed', value: 'processed' },
]

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '消息ID', key: 'message_id', width: 100, align: 'center' },
  { title: '用户ID', key: 'user_id', width: 100, align: 'center' },
  { title: '评分', key: 'rating', width: 80, align: 'center' },
  { title: '反馈内容', key: 'comment', align: 'left' },
  { title: '状态', key: 'status', width: 100, align: 'center' },
  { title: '创建时间', key: 'created_at', width: 180, align: 'center' },
]

async function getData(params = {}) {
  const res = await api.kbFeedbackList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}
</script>

<template>
  <CommonPage title="反馈标注" show-footer>
    <CrudTable ref="tableRef" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
      <template #queryBar>
        <QueryBarItem label="状态" :label-width="60">
          <NSelect v-model:value="queryItems.status" :options="statusOptions" clearable placeholder="状态" />
        </QueryBarItem>
        <QueryBarItem label="备注" :label-width="60">
          <NInput value="MVP仅展示反馈列表" readonly />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
