<template>
  <NPopover trigger="click" placement="bottom-end" :width="420">
    <template #trigger>
      <NBadge :value="unreadCount" :max="99" :show="unreadCount > 0">
        <NButton quaternary circle>
          <template #icon>
            <icon-mdi:bell-outline />
          </template>
        </NButton>
      </NBadge>
    </template>

    <div class="notice-panel">
      <div class="notice-head">
        <strong>消息通知</strong>
        <NButton text size="small" @click="readAll">全部已读</NButton>
      </div>
      <div v-if="loading" class="notice-loading">加载中...</div>
      <div v-else-if="!rows.length" class="notice-empty">暂无通知</div>
      <div v-else class="notice-list">
        <div v-for="item in rows" :key="item.notice_id" class="notice-item" :class="{ unread: !item.is_read }">
          <div class="notice-item-head">
            <span class="notice-title">{{ item.title || '系统通知' }}</span>
            <NButton v-if="!item.is_read" text size="tiny" @click="markRead(item.notice_id)">已读</NButton>
          </div>
          <div class="notice-content" v-html="sanitizeHtml(item.content_html || '')"></div>
        </div>
      </div>
    </div>
  </NPopover>

  <NModal v-model:show="previewVisible" preset="card" title="最新通知" style="width: 840px" :mask-closable="true">
    <div class="notice-preview-shell">
      <div class="notice-preview-list">
        <div class="notice-preview-head">最近10条</div>
        <div
          v-for="item in rows"
          :key="`preview-${item.notice_id}`"
          class="notice-preview-item"
          :class="{ active: currentNotice?.notice_id === item.notice_id, unread: !item.is_read }"
          @click="selectNotice(item)"
        >
          <div class="preview-item-title">{{ item.title || '系统通知' }}</div>
          <div class="preview-item-time">{{ item.created_at || '-' }}</div>
        </div>
      </div>
      <div class="notice-preview-detail" v-if="currentNotice">
        <div class="preview-detail-head">
          <div>
            <h3>{{ currentNotice.title || '系统通知' }}</h3>
            <div class="preview-detail-time">{{ currentNotice.created_at || '-' }}</div>
          </div>
          <div class="preview-detail-actions">
            <NTag :type="currentNotice.is_read ? 'default' : 'warning'">{{ currentNotice.is_read ? '已读' : '未读' }}</NTag>
            <NButton v-if="!currentNotice.is_read" size="small" type="primary" ghost @click="markRead(currentNotice.notice_id)">标记已读</NButton>
          </div>
        </div>
        <div class="preview-detail-content" v-html="sanitizeHtml(currentNotice.content_html || '')"></div>
      </div>
      <div v-else class="notice-empty">暂无通知</div>
    </div>
  </NModal>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { NBadge, NButton, NModal, NPopover, NTag } from 'naive-ui'
import api from '@/api'
import { sanitizeHtml } from '@/utils'

const unreadCount = ref(0)
const rows = ref([])
const loading = ref(false)
const previewVisible = ref(false)
const currentNotice = ref(null)

async function refreshUnread() {
  const res = await api.getNoticeUnreadCount()
  unreadCount.value = Number(res?.data?.unread_count || 0)
}

async function loadInbox() {
  try {
    loading.value = true
    const res = await api.getNoticeInbox({ page: 1, page_size: 10 })
    rows.value = Array.isArray(res?.data) ? res.data : []
  } finally {
    loading.value = false
  }
}

function selectNotice(item) {
  currentNotice.value = item
}

async function markRead(noticeId) {
  await api.readNotice({ notice_id: noticeId })
  await Promise.all([refreshUnread(), loadInbox()])
  if (currentNotice.value && currentNotice.value.notice_id === noticeId) {
    currentNotice.value.is_read = true
  }
}

async function readAll() {
  await api.readAllNotice()
  await Promise.all([refreshUnread(), loadInbox()])
  if (currentNotice.value) {
    currentNotice.value.is_read = true
  }
}

onMounted(async () => {
  await Promise.all([refreshUnread(), loadInbox()])
  if (unreadCount.value > 0 && rows.value.length) {
    const firstUnread = rows.value.find((item) => !item.is_read)
    currentNotice.value = firstUnread || rows.value[0]
    previewVisible.value = true
  }
})
</script>

<style scoped>
.notice-panel { max-height: 460px; overflow-y: auto; }
.notice-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.notice-loading,.notice-empty { color: #6b7280; font-size: 13px; padding: 8px 0; }
.notice-list { display: flex; flex-direction: column; gap: 10px; }
.notice-item { padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.notice-item.unread { border-color: #bfdbfe; background: #f8fbff; }
.notice-item-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.notice-title { font-size: 13px; font-weight: 600; color: #111827; }
.notice-content { color: #374151; font-size: 13px; line-height: 1.6; }

.notice-preview-shell { display: grid; grid-template-columns: 240px 1fr; gap: 14px; min-height: 420px; }
.notice-preview-list { border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; overflow: hidden; box-shadow: inset 0 1px 0 #fff; }
.notice-preview-head { padding: 10px 12px; font-size: 13px; font-weight: 600; background: #f9fafb; border-bottom: 1px solid #eef1f5; }
.notice-preview-item { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; cursor: pointer; }
.notice-preview-item:hover { background: #f8fbff; }
.notice-preview-item.active { background: #eef6ff; }
.notice-preview-item.unread .preview-item-title { color: #1d4ed8; }
.notice-preview-item.unread { border-left: 3px solid #60a5fa; }
.preview-item-title { font-size: 13px; font-weight: 600; color: #111827; }
.preview-item-time { margin-top: 4px; font-size: 12px; color: #6b7280; }

.notice-preview-detail { border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; padding: 16px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); }
.preview-detail-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.preview-detail-actions { display: flex; align-items: center; gap: 8px; }
.preview-detail-head h3 { margin: 0; font-size: 20px; color: #111827; }
.preview-detail-time { margin-top: 6px; font-size: 12px; color: #6b7280; }
.preview-detail-content {
  margin-top: 14px;
  color: #374151;
  line-height: 1.75;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}
</style>
