<script setup>
import { h, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import api from '@/api'

defineOptions({ name: '我的工单' })

const $table = ref(null)
const route = useRoute()
const queryItems = ref({
  status: route.query.status || undefined,
  created_start: route.query.created_start || undefined,
  created_end: route.query.created_end || undefined,
  finished_start: route.query.finished_start || undefined,
  finished_end: route.query.finished_end || undefined,
})
const detailVisible = ref(false)
const currentTicket = ref({})

const statusTypeMap = {
  pending_review: 'warning',
  cs_rejected: 'error',
  tech_processing: 'info',
  tech_rejected: 'error',
  done: 'success',
}

const statusTextMap = {
  pending_review: '审核中',
  cs_rejected: '客服驳回',
  tech_processing: '技术处理中',
  tech_rejected: '技术驳回',
  done: '已完成',
}

onMounted(() => {
  $table.value?.handleSearch()
})

async function openDetail(row) {
  const res = await api.getTicketById({ ticket_id: row.id })
  currentTicket.value = res.data
  detailVisible.value = true
}

const columns = [
  { title: '工单编号', key: 'ticket_no', align: 'center' },
  { title: '问题分类', key: 'category', align: 'center' },
  { title: '标题', key: 'title', align: 'center', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      return h(NTag, { type: statusTypeMap[row.status] || 'default' }, { default: () => statusTextMap[row.status] })
    },
  },
  { title: '创建时间', key: 'created_at', align: 'center' },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'primary', onClick: () => openDetail(row) },
        { default: () => '详情' }
      )
    },
  },
]
</script>

<template>
  <CommonPage title="我的工单" show-footer>
    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getTicketList">
      <template #queryBar>
        <QueryBarItem label="标题" :label-width="40">
          <n-input v-model:value="queryItems.title" clearable placeholder="输入标题" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
        <QueryBarItem label="分类" :label-width="40">
          <n-input v-model:value="queryItems.category" clearable placeholder="输入分类" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal v-model:visible="detailVisible" title="工单详情" width="800px" :show-footer="false">
      <div><strong>编号：</strong>{{ currentTicket.ticket_no }}</div>
      <div mt-8><strong>公司：</strong>{{ currentTicket.company_name }}</div>
      <div mt-8><strong>联系人：</strong>{{ currentTicket.contact_name }}</div>
      <div mt-8><strong>标题：</strong>{{ currentTicket.title }}</div>
      <div mt-8><strong>描述：</strong>{{ currentTicket.description }}</div>
      <div mt-12><strong>流转日志：</strong></div>
      <n-timeline mt-8>
        <n-timeline-item
          v-for="item in currentTicket.actions || []"
          :key="item.id"
          :title="item.action"
          :content="item.comment || '-'"
          :time="item.created_at"
        />
      </n-timeline>
    </CrudModal>
  </CommonPage>
</template>
