<script setup>
import { h, nextTick, onMounted, ref } from 'vue'
import { NButton, NPopconfirm, NSwitch, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '分享记录' })

const shareTable = ref(null)
const shareQuery = ref({ include_history: false })

onMounted(async () => {
  await nextTick()
  shareTable.value?.handleSearch()
})

async function getShareTableData(params = {}) {
  const res = await api.webdavShareList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

const shareColumns = [
  { title: '分享码', key: 'code', width: 120, align: 'center' },
  { title: '创建者', key: 'creator_name', width: 120, align: 'center' },
  { title: '文件名', key: 'file_name', align: 'left' },
  { title: '文件路径', key: 'file_path', align: 'left' },
  { title: '过期时间', key: 'expire_time', width: 180, align: 'center' },
  {
    title: '状态',
    key: 'is_active',
    width: 90,
    align: 'center',
    render(row) {
      return h(NTag, { type: row.is_active ? 'success' : 'default', bordered: false }, { default: () => (row.is_active ? '生效' : '失效') })
    },
  },
  {
    title: '下载链接',
    key: 'link',
    width: 280,
    align: 'left',
    render(row) {
      const origin = window.location.origin
      const url = `${origin}/api/v1/public/webdav/share/download?code=${row.code}`
      const disabled = !row.is_active
      return h(
        NButton,
        {
          type: 'primary',
          text: true,
          disabled,
          onClick: async () => {
            if (disabled) return
            await navigator.clipboard.writeText(url)
            $message.success('下载链接已复制')
          },
        },
        { default: () => (disabled ? '已失效' : url) }
      )
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NPopconfirm,
        { onPositiveClick: () => deleteShare(row.id) },
        {
          trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除该分享记录？',
        }
      )
    },
  },
]

async function deleteShare(id) {
  await api.webdavShareDelete({ id })
  $message.success('分享记录已删除')
  shareTable.value?.handleSearch()
}
</script>

<template>
  <CommonPage title="分享记录" show-footer>
    <CrudTable
      ref="shareTable"
      v-model:query-items="shareQuery"
      :columns="shareColumns"
      :get-data="getShareTableData"
    >
      <template #queryBar>
        <QueryBarItem label="显示历史" :label-width="70">
          <NSwitch v-model:value="shareQuery.include_history" />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>
