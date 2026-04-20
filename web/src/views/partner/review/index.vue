<script setup>
import { h, onMounted, ref } from 'vue'
import { NButton, NInput, NTag, NModal, NForm, NFormItem } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '注册审核' })

const $table = ref(null)
const queryItems = ref({ status: 'pending' })
const rejectModalVisible = ref(false)
const rejectSubmitting = ref(false)
const rejectingRow = ref(null)
const rejectFormRef = ref(null)
const rejectForm = ref({
  reason: '',
})

onMounted(() => {
  $table.value?.handleSearch()
})

async function review(row, approved) {
  await api.reviewPartnerRegister({
    id: row.id,
    approved,
    comment: approved ? '审核通过' : '审核驳回',
  })
  $message.success('审核完成')
  $table.value?.handleSearch()
}

function openRejectModal(row) {
  rejectingRow.value = row
  rejectForm.value.reason = ''
  rejectModalVisible.value = true
}

function submitReject() {
  rejectFormRef.value?.validate(async (err) => {
    if (err) return
    try {
      rejectSubmitting.value = true
      await api.reviewPartnerRegister({
        id: rejectingRow.value.id,
        approved: false,
        comment: rejectForm.value.reason,
      })
      $message.success('驳回完成')
      rejectModalVisible.value = false
      $table.value?.handleSearch()
    } finally {
      rejectSubmitting.value = false
    }
  })
}

const columns = [
  { title: '公司名称', key: 'company_name', align: 'center' },
  { title: '联系人', key: 'contact_name', align: 'center' },
  { title: '邮箱', key: 'email', align: 'center' },
  { title: '手机号', key: 'phone', align: 'center' },
  { title: '用户名', key: 'username', align: 'center' },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      const type = row.status === 'pending' ? 'warning' : row.status === 'approved' ? 'success' : 'error'
      return h(NTag, { type }, { default: () => row.status })
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render(row) {
      if (row.status !== 'pending') return '-'
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
          NButton,
          { size: 'small', type: 'error', onClick: () => openRejectModal(row) },
          {
            default: () => '驳回',
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage title="代理商注册审核" show-footer>
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getPartnerRegisterList"
    >
      <template #queryBar>
        <QueryBarItem label="关键词" :label-width="50">
          <NInput
            v-model:value="queryItems.keyword"
            clearable
            placeholder="公司/联系人/邮箱"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <NModal v-model:show="rejectModalVisible" preset="card" title="驳回注册申请" style="width: 520px">
      <NForm ref="rejectFormRef" :model="rejectForm" :rules="{ reason: { required: true, message: '请填写驳回理由', trigger: ['blur', 'input'] } }">
        <NFormItem label="驳回理由" path="reason">
          <NInput v-model:value="rejectForm.reason" type="textarea" placeholder="请输入驳回理由（将通过邮件通知用户）" />
        </NFormItem>
      </NForm>
      <template #footer>
        <div flex justify-end>
          <NButton @click="rejectModalVisible = false">取消</NButton>
          <NButton ml-12 type="error" :loading="rejectSubmitting" @click="submitReject">确认驳回</NButton>
        </div>
      </template>
    </NModal>
  </CommonPage>
</template>
