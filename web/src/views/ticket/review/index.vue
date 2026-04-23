<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { NButton, NCard, NInput, NModal, NSelect, NPopconfirm, NSpace, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TicketDetailModal from '@/views/ticket/components/TicketDetailModal.vue'
import api from '@/api'
import { ticketStatusOptions, ticketStatusTextMap, ticketStatusTypeMap } from '@/views/ticket/components/ticket-meta'

defineOptions({ name: '工单审核' })

const $table = ref(null)
const queryItems = ref({ status: 'pending_review' })
const tableData = ref([])
const detailVisible = ref(false)
const currentTicket = ref({})
const commentVisible = ref(false)
const reviewAction = ref(true)
const pendingReviewRow = ref(null)
const reviewComment = ref('')
const rootCauseOptions = ref([])
const categoryOptions = ref([])
const projectPhaseOptions = ref([])
const quickFilters = [
  { label: '待审核', value: 'pending_review' },
  { label: '已驳回', value: 'cs_rejected' },
  { label: '流转技术', value: 'tech_processing' },
]

const summaryCards = computed(() => {
  const rows = tableData.value || []
  const countByStatus = rows.reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1
    return acc
  }, {})
  return [
    { label: '待审核工单', value: countByStatus.pending_review || 0, tone: 'warning' },
    { label: '已驳回', value: countByStatus.cs_rejected || 0, tone: 'error' },
    { label: '已流转技术', value: countByStatus.tech_processing || 0, tone: 'info' },
  ]
})

onMounted(() => {
  $table.value?.handleSearch()
  loadCategoryOptions()
  loadRootCauseOptions()
  loadProjectPhaseOptions()
})

async function loadProjectPhaseOptions() {
  try {
    const res = await api.getSystemSettings()
    projectPhaseOptions.value = (res?.data?.ticket_project_phases || []).map((item) => ({ label: item, value: item }))
  } catch (error) {
    projectPhaseOptions.value = []
  }
}

async function loadCategoryOptions() {
  try {
    const res = await api.getSystemSettings()
    categoryOptions.value = (res?.data?.ticket_categories || []).map((item) => ({ label: item, value: item }))
  } catch (error) {
    categoryOptions.value = []
  }
}

async function loadRootCauseOptions() {
  try {
    const res = await api.getSystemSettings()
    rootCauseOptions.value = (res?.data?.ticket_root_causes || []).map((item) => ({ label: item, value: item }))
  } catch (error) {
    rootCauseOptions.value = []
  }
}

async function review(row, approved) {
  await api.reviewTicket({
    ticket_id: row.id,
    approved,
    comment: reviewComment.value?.trim() || (approved ? '审核通过' : '客服驳回'),
  })
  $message.success('审核操作已完成')
  commentVisible.value = false
  pendingReviewRow.value = null
  reviewComment.value = ''
  $table.value?.handleSearch()
}

async function openDetail(row) {
  const res = await api.getTicketById({ ticket_id: row.id })
  currentTicket.value = res.data
  detailVisible.value = true
}

function applyQuickFilter(status) {
  queryItems.value.status = status
  $table.value?.handleSearch()
}

function openReviewAction(row, approved) {
  pendingReviewRow.value = row
  reviewAction.value = approved
  reviewComment.value = approved ? '审核通过' : '客服驳回'
  commentVisible.value = true
}

async function submitReviewAction() {
  if (!pendingReviewRow.value) return
  await review(pendingReviewRow.value, reviewAction.value)
}

const columns = [
  { title: '工单编号', key: 'ticket_no', align: 'center' },
  { title: '提交人', key: 'submitter_id', align: 'center' },
  { title: '标题', key: 'title', align: 'center', ellipsis: { tooltip: true } },
  { title: '项目阶段', key: 'project_phase', align: 'center' },
  { title: '分类', key: 'category', align: 'center' },
  { title: '问题根因', key: 'root_cause', align: 'center', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      return h(NTag, { type: ticketStatusTypeMap[row.status] || 'default' }, { default: () => ticketStatusTextMap[row.status] })
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    render(row) {
      return [
        h(
          NButton,
          {
            size: 'small',
            quaternary: true,
            type: 'default',
            style: 'margin-right: 8px',
            onClick: () => openDetail(row),
          },
          { default: () => '详情' }
        ),
        ...(row.status !== 'pending_review'
          ? []
          : [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            style: 'margin-right: 8px',
            onClick: () => openReviewAction(row, true),
          },
          { default: () => '通过' }
        ),
        h(
          NButton,
          { size: 'small', type: 'error', onClick: () => openReviewAction(row, false) },
          { default: () => '驳回' }
        ),
            ]),
      ]
    },
  },
]
</script>

<template>
  <CommonPage title="工单审核" show-footer>
    <div class="ticket-review-page">
      <div class="hero-panel review-hero">
        <div>
          <div class="hero-kicker">Review Queue</div>
          <h2>工单审核台</h2>
          <p>客服在这里统一筛查提交内容、确认问题归类，并将有效问题流转给技术处理。</p>
        </div>
        <div class="hero-badge">客服视角</div>
      </div>

      <div class="summary-grid review-grid">
        <div v-for="item in summaryCards" :key="item.label" class="summary-card" :data-tone="item.tone">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>

      <NSpace>
        <NButton
          v-for="item in quickFilters"
          :key="item.value"
          round
          :type="queryItems.status === item.value ? 'primary' : 'default'"
          :quaternary="queryItems.status !== item.value"
          @click="applyQuickFilter(item.value)"
        >
          {{ item.label }}
        </NButton>
      </NSpace>

      <NCard size="small" class="table-shell">
        <CrudTable
          ref="$table"
          v-model:query-items="queryItems"
          :columns="columns"
          :get-data="api.getTicketList"
          @on-data-change="(rows) => (tableData = rows)"
        >
          <template #queryBar>
            <QueryBarItem label="标题" :label-width="40">
              <NInput v-model:value="queryItems.title" clearable placeholder="输入标题" @keypress.enter="$table?.handleSearch()" />
            </QueryBarItem>
            <QueryBarItem label="分类" :label-width="40">
              <NSelect v-model:value="queryItems.category" :options="categoryOptions" clearable placeholder="选择分类" />
            </QueryBarItem>
            <QueryBarItem label="阶段" :label-width="40">
              <NSelect v-model:value="queryItems.project_phase" :options="projectPhaseOptions" clearable placeholder="选择阶段" />
            </QueryBarItem>
            <QueryBarItem label="状态" :label-width="40">
              <NSelect v-model:value="queryItems.status" :options="ticketStatusOptions" clearable placeholder="选择状态" />
            </QueryBarItem>
            <QueryBarItem label="根因" :label-width="40">
              <NSelect v-model:value="queryItems.root_cause" :options="rootCauseOptions" clearable placeholder="选择问题根因" />
            </QueryBarItem>
          </template>
        </CrudTable>
      </NCard>

      <TicketDetailModal v-model:visible="detailVisible" :ticket="currentTicket" />

      <NModal v-model:show="commentVisible" preset="card" style="width: 520px" :title="reviewAction ? '审核通过备注' : '驳回备注'">
        <NInput
          v-model:value="reviewComment"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 6 }"
          :placeholder="reviewAction ? '可填写审核说明' : '请填写驳回原因'"
        />
        <div class="modal-actions">
          <NButton @click="commentVisible = false">取消</NButton>
          <NButton type="primary" @click="submitReviewAction">确认提交</NButton>
        </div>
      </NModal>
    </div>
  </CommonPage>
</template>

<style scoped>
.ticket-review-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 26px;
  border-radius: 20px;
  color: #fff;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.14);
}

.review-hero {
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.18), transparent 30%),
    linear-gradient(135deg, #7c2d12 0%, #c2410c 48%, #fb923c 100%);
}

.hero-kicker {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
}

.hero-panel h2 {
  margin: 0;
  font-size: 30px;
}

.hero-panel p {
  max-width: 620px;
  margin: 10px 0 0;
  line-height: 1.7;
  opacity: 0.92;
}

.hero-badge {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 13px;
  font-weight: 600;
}

.summary-grid {
  display: grid;
  gap: 14px;
}

.review-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.summary-card {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid #ebeef5;
  background: #fff;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.05);
}

.summary-card span {
  display: block;
  color: #6b7280;
  font-size: 13px;
}

.summary-card strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  line-height: 1;
  color: #111827;
}

.summary-card[data-tone='warning'] {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
}

.summary-card[data-tone='error'] {
  background: linear-gradient(180deg, #fff1f2 0%, #ffffff 100%);
}

.summary-card[data-tone='info'] {
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
}

.table-shell {
  border-radius: 20px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 900px) {
  .review-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-panel {
    padding: 18px;
  }

  .hero-panel h2 {
    font-size: 24px;
  }

  .hero-badge {
    display: none;
  }
}
</style>
