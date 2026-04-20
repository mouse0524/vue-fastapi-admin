<script setup>
import { h, onMounted, ref } from 'vue'
import { NButton, NInput, NPopconfirm, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '技术处理' })

const $table = ref(null)
const queryItems = ref({ status: 'tech_processing' })

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

async function takeAction(row, action) {
  await api.techActionTicket({
    ticket_id: row.id,
    action,
    comment: action === 'finish' ? '技术处理完成' : action === 'tech_reject' ? '技术驳回' : '处理中',
  })
  $message.success('操作成功')
  $table.value?.handleSearch()
}

const columns = [
  { title: '工单编号', key: 'ticket_no', align: 'center' },
  { title: '标题', key: 'title', align: 'center', ellipsis: { tooltip: true } },
  { title: '分类', key: 'category', align: 'center' },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.status === 'tech_processing' ? 'info' : row.status === 'done' ? 'success' : 'default' },
        { default: () => statusTextMap[row.status] }
      )
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render(row) {
      if (row.status !== 'tech_processing') return '-'
      return [
        h(
          NButton,
          {
            size: 'small',
            type: 'success',
            style: 'margin-right: 8px',
            onClick: () => takeAction(row, 'finish'),
          },
          { default: () => '完成' }
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => takeAction(row, 'tech_reject') },
          {
            trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '驳回' }),
            default: () => '确认技术驳回该工单吗？',
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage title="技术处理" show-footer>
    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="api.getTicketList">
      <template #queryBar>
        <QueryBarItem label="标题" :label-width="40">
          <NInput v-model:value="queryItems.title" clearable placeholder="输入标题" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
        <QueryBarItem label="状态" :label-width="40">
          <NInput v-model:value="queryItems.status" clearable placeholder="tech_processing" @keypress.enter="$table?.handleSearch()" />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
