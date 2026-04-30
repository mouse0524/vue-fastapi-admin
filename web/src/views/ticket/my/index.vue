<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NCard, NSelect, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import TicketDetailModal from '@/views/ticket/components/TicketDetailModal.vue'
import api from '@/api'
import { ticketStatusOptions, ticketStatusTextMap, ticketStatusTypeMap } from '@/views/ticket/components/ticket-meta'

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
const tableData = ref([])
const rootCauseOptions = ref([])
const categoryOptions = ref([])
const projectPhaseOptions = ref([])

const summaryCards = computed(() => {
  const rows = tableData.value || []
  const countByStatus = rows.reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1
    return acc
  }, {})
  return [
    { label: '当前总工单', value: rows.length, tone: 'neutral' },
    { label: '审核中', value: countByStatus.pending_review || 0, tone: 'warning' },
    { label: '技术处理中', value: countByStatus.tech_processing || 0, tone: 'info' },
    { label: '已完成', value: countByStatus.done || 0, tone: 'success' },
  ]
})

onMounted(() => {
  $table.value?.handleSearch()
  loadTicketMetaOptions()
})

async function loadTicketMetaOptions() {
  try {
    const res = await api.getSystemSettings()
    const config = res?.data || {}
    projectPhaseOptions.value = (config.ticket_project_phases || []).map((item) => ({ label: item, value: item }))
    categoryOptions.value = (config.ticket_categories || []).map((item) => ({ label: item, value: item }))
    rootCauseOptions.value = (config.ticket_root_causes || []).map((item) => ({ label: item, value: item }))
  } catch (error) {
    rootCauseOptions.value = []
    categoryOptions.value = []
    projectPhaseOptions.value = []
  }
}

async function openDetail(row) {
  const res = await api.getTicketById({ ticket_id: row.id })
  currentTicket.value = res.data
  detailVisible.value = true
}

const columns = [
  { title: '工单编号', key: 'ticket_no', align: 'center' },
  { title: '项目阶段', key: 'project_phase', align: 'center' },
  { title: '问题分类', key: 'category', align: 'center' },
  { title: '标题', key: 'title', align: 'center', ellipsis: { tooltip: true } },
  { title: '问题根因', key: 'root_cause', align: 'center', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render(row) {
      return h(NTag, { type: ticketStatusTypeMap[row.status] || 'default' }, { default: () => ticketStatusTextMap[row.status] })
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
    <div class="ticket-my-page">
      <div class="hero-panel">
        <div>
          <div class="hero-kicker">Ticket Center</div>
          <h2>我的工单</h2>
          <p>集中查看当前处理状态、历史流转记录与问题进展，跟踪每一张工单的处理节奏。</p>
        </div>
        <div class="hero-rings">
          <div class="ring ring-a"></div>
          <div class="ring ring-b"></div>
        </div>
      </div>

      <div class="summary-grid">
        <div v-for="item in summaryCards" :key="item.label" class="summary-card" :data-tone="item.tone">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>

      <NCard size="small" class="table-shell">
        <CrudTable
          ref="$table"
          v-model:query-items="queryItems"
          :columns="columns"
          :get-data="api.getTicketList"
          @on-data-change="(rows) => (tableData.value = rows)"
        >
          <template #queryBar>
            <QueryBarItem label="标题" :label-width="40">
              <n-input v-model:value="queryItems.title" clearable placeholder="输入标题" @keypress.enter="$table?.handleSearch()" />
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
    </div>
  </CommonPage>
</template>

<style scoped>
.ticket-my-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-panel {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  overflow: hidden;
  padding: 24px 26px;
  border-radius: 20px;
  color: #fff;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.16), transparent 32%),
    linear-gradient(135deg, #1f2937 0%, #374151 42%, #b45309 100%);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.14);
}

.hero-kicker {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.82;
}

.hero-panel h2 {
  margin: 0;
  font-size: 30px;
}

.hero-panel p {
  max-width: 620px;
  margin: 10px 0 0;
  line-height: 1.7;
  opacity: 0.9;
}

.hero-rings {
  position: relative;
  width: 180px;
  height: 110px;
}

.ring {
  position: absolute;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.ring-a {
  width: 120px;
  height: 120px;
  right: -20px;
  top: -12px;
}

.ring-b {
  width: 72px;
  height: 72px;
  right: 56px;
  top: 34px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
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
  background: linear-gradient(180deg, #fffaf0 0%, #ffffff 100%);
}

.summary-card[data-tone='info'] {
  background: linear-gradient(180deg, #f3f8ff 0%, #ffffff 100%);
}

.summary-card[data-tone='success'] {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
}

.table-shell {
  border-radius: 20px;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-rings {
    display: none;
  }
}

@media (max-width: 640px) {
  .hero-panel {
    padding: 18px;
  }

  .hero-panel h2 {
    font-size: 24px;
  }

  .summary-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
