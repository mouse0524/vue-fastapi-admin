<script setup>
import { computed } from 'vue'
import { NButton, NEmpty, NTag } from 'naive-ui'
import CrudModal from '@/components/table/CrudModal.vue'
import { mapTicketActionText, ticketStatusTextMap, ticketStatusTypeMap } from './ticket-meta'

defineEmits(['update:visible'])

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  ticket: {
    type: Object,
    default() {
      return {}
    },
  },
})

const attachments = computed(() => props.ticket?.attachments || [])

function openAttachment(item) {
  if (!item?.id) return
  const url = `/api/v1/ticket/attachment/download?attachment_id=${encodeURIComponent(item.id)}`
  window.open(url, '_blank')
}

async function copyText(text, successText) {
  if (!text) return
  await navigator.clipboard.writeText(String(text))
  $message.success(successText)
}

function renderActionContent(item) {
  if (!item) return '-'
  if (item.action === 'finish' && props.ticket?.root_cause) {
    const base = item.comment?.trim() || '处理完成'
    return `${base}（根因：${props.ticket.root_cause}）`
  }
  return item.comment || '-'
}
</script>

<template>
  <CrudModal :visible="visible" title="工单详情" width="880px" :show-footer="false" @update:visible="$emit('update:visible', $event)">
    <div class="detail-header">
      <div>
        <div class="detail-no">{{ ticket.ticket_no }}</div>
        <div class="detail-title">{{ ticket.title }}</div>
        <div class="detail-actions">
          <NButton size="tiny" quaternary type="primary" @click="copyText(ticket.ticket_no, '工单编号已复制')">复制编号</NButton>
          <NButton size="tiny" quaternary type="primary" @click="copyText(ticket.description, '问题描述已复制')">复制描述</NButton>
        </div>
      </div>
      <NTag :type="ticketStatusTypeMap[ticket.status] || 'default'">{{ ticketStatusTextMap[ticket.status] || '-' }}</NTag>
    </div>

    <div class="detail-grid">
      <div class="detail-card">
        <span>公司名称</span>
        <strong>{{ ticket.company_name || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>联系人</span>
        <strong>{{ ticket.contact_name || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>项目阶段</span>
        <strong>{{ ticket.project_phase || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>问题分类</span>
        <strong>{{ ticket.category || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>创建时间</span>
        <strong>{{ ticket.created_at || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>提交人</span>
        <strong>{{ ticket.submitter_name || ticket.submitter_id || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>附件数量</span>
        <strong>{{ attachments.length }}</strong>
      </div>
      <div class="detail-card">
        <span>客服审核人</span>
        <strong>{{ ticket.reviewer_id || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>技术处理人</span>
        <strong>{{ ticket.tech_id || '-' }}</strong>
      </div>
      <div class="detail-card">
        <span>问题根因</span>
        <strong>{{ ticket.root_cause || '-' }}</strong>
      </div>
      <div class="detail-card detail-card-wide">
        <span>完成时间</span>
        <strong>{{ ticket.finished_at || '-' }}</strong>
      </div>
    </div>

    <div class="description-card">
      <div class="section-title">问题描述</div>
      <div class="description-content" v-html="ticket.description || '-'"></div>
    </div>

    <div class="attachment-card">
      <div class="section-title">附件列表</div>
      <div v-if="attachments.length" class="attachment-list">
        <div v-for="item in attachments" :key="item.id" class="attachment-item">
          <div>
            <div class="attachment-name">{{ item.origin_name || item.file_path }}</div>
            <div class="attachment-meta">{{ item.mime_type || 'application/octet-stream' }} / {{ item.file_size || 0 }} bytes</div>
          </div>
          <NButton size="small" type="primary" quaternary @click="openAttachment(item)">下载</NButton>
        </div>
      </div>
      <NEmpty v-else description="暂无附件" size="small" />
    </div>

    <div class="timeline-card">
      <div class="section-title">流转日志</div>
      <n-timeline class="ticket-timeline">
        <n-timeline-item
          v-for="item in ticket.actions || []"
          :key="item.id"
          :title="mapTicketActionText(item.action)"
          :content="renderActionContent(item)"
          :time="item.created_at"
        />
      </n-timeline>
    </div>
  </CrudModal>
</template>

<style scoped>
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.detail-no {
  color: #9ca3af;
  font-size: 13px;
}

.detail-title {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.detail-card,
.description-card,
.attachment-card,
.timeline-card {
  padding: 16px;
  border: 1px solid #eceff5;
  border-radius: 18px;
  background: #fafbfd;
}

.detail-card span,
.section-title {
  display: block;
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.detail-card strong {
  display: block;
  margin-top: 8px;
  color: #111827;
  font-size: 15px;
}

.detail-card-wide {
  grid-column: span 2;
}

.description-card,
.attachment-card,
.timeline-card {
  margin-top: 14px;
}

.description-content {
  margin-top: 10px;
  color: #374151;
  line-height: 1.8;
  word-break: break-word;
}

.ticket-timeline {
  margin-top: 10px;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.attachment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.attachment-name {
  color: #111827;
  font-weight: 600;
}

.attachment-meta {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

@media (max-width: 960px) {
  .detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-card-wide {
    grid-column: span 1;
  }
}
</style>
