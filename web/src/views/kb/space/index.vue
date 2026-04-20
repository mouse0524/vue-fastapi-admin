<script setup>
import { ref } from 'vue'
import { NButton, NInput, NSpace } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import api from '@/api'

defineOptions({ name: '知识空间' })

const tableRef = ref(null)
const queryItems = ref({ keyword: '' })
const form = ref({ name: '', desc: '' })

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '空间名称', key: 'name', align: 'left' },
  { title: '描述', key: 'desc', align: 'left' },
  { title: '创建人ID', key: 'owner_id', width: 100, align: 'center' },
  { title: '更新时间', key: 'updated_at', width: 180, align: 'center' },
]

async function getData(params = {}) {
  const res = await api.kbSpaceList(params)
  return {
    data: res?.data || [],
    total: Number(res?.total || 0),
  }
}

async function createSpace() {
  if (!form.value.name?.trim()) {
    $message.warning('请输入空间名称')
    return
  }
  await api.kbSpaceCreate({ name: form.value.name.trim(), desc: form.value.desc || null, is_public: false, status: true })
  form.value = { name: '', desc: '' }
  $message.success('创建成功')
  tableRef.value?.handleSearch()
}
</script>

<template>
  <CommonPage title="知识空间" show-footer>
    <NSpace vertical>
      <NSpace>
        <NInput v-model:value="form.name" placeholder="空间名称" style="width: 220px" />
        <NInput v-model:value="form.desc" placeholder="空间描述" style="width: 360px" />
        <NButton type="primary" @click="createSpace">新建空间</NButton>
      </NSpace>

      <CrudTable ref="tableRef" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
        <template #queryBar>
          <QueryBarItem label="关键字" :label-width="60">
            <NInput v-model:value="queryItems.keyword" clearable placeholder="空间名关键字" />
          </QueryBarItem>
        </template>
      </CrudTable>
    </NSpace>
  </CommonPage>
</template>
