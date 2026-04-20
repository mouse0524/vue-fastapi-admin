<script setup>
import { h, onMounted, ref } from 'vue'
import { NButton, NInput, NPopconfirm, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '工单审核' })

const $table = ref(null)
const queryItems = ref({ status: 'pending_review' })

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

async function review(row, approved) {
  await api.reviewTicket({
    ticket_id: row.id,
    approved,
    comment: approved ? '审核通过' : '客服驳回',
  })
  $message.success('操作成功')
  $table.value?.handleSearch()
}

const columns = [
  { title: '工单编号', key: 'ticket_no', align: 'center' },
  { title: '提交人', key: 'submitter_id', align: 'center' },
  { title: '标题', key: 'title', align: 'center', ellipsis: { tooltip: true } },
  { title: '分类', key: 'category', align: 'center' },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      return h(NTag, { type: row.status === 'pending_review' ? 'warning' : 'default' }, { default: () => statusTextMap[row.status] })
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render(row) {
      if (row.status !== 'pending_review') return '-'
      return [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            style: 'margin-right: 8px',
            onClick: () => review(row, true),
          },
          { default: () => '通过' }
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => review(row, false) },
          {
            trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '驳回' }),
            default: () => '确认驳回该工单吗？',
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage title="工单审核" show-footer>
    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getTicketList">
      <template #queryBar>
        <QueryBarItem label="标题" :label-width="40">
          <NInput v-model:value="queryItems.title" clearable placeholder="输入标题" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
        <QueryBarItem label="状态" :label-width="40">
          <NInput v-model:value="queryItems.status" clearable placeholder="pending_review" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
