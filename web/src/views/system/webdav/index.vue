<script setup>
import { computed, h, nextTick, onMounted, ref } from 'vue'
import { NButton, NCard, NSpace } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'

defineOptions({ name: '外发网盘' })

const currentPath = ref('/')
const fileList = ref([])
const loading = ref(false)
const fileTable = ref(null)
const creatingSharePath = ref('')
const isCreatingShare = computed(() => !!creatingSharePath.value)

const breadcrumbItems = computed(() => {
  const clean = (currentPath.value || '/').replace(/^\/+|\/+$/g, '')
  const items = [{ label: 'home', path: '/' }]
  if (!clean) return items
  const parts = clean.split('/')
  for (let idx = 0; idx < parts.length; idx += 1) {
    items.push({
      label: parts[idx],
      path: '/' + parts.slice(0, idx + 1).join('/'),
    })
  }
  return items
})

async function getFileTableData() {
  return {
    data: fileList.value,
    total: fileList.value.length,
  }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let idx = 0
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx += 1
  }
  return `${size.toFixed(size >= 100 || idx === 0 ? 0 : 1)} ${units[idx]}`
}

const fileColumns = [
  {
    title: '名称',
    key: 'name',
    align: 'left',
    render(row) {
      if (row.is_dir) {
        return h(
          NButton,
          { type: 'primary', text: true, onClick: () => openDir(row.path) },
          { default: () => `📁 ${row.name}` }
        )
      }
      return h('span', `📄 ${row.name}`)
    },
  },
  {
    title: '大小',
    key: 'size',
    width: 120,
    align: 'center',
    render(row) {
      if (row.is_dir) return '-'
      return formatSize(row.size || 0)
    },
  },
  { title: '修改时间', key: 'mod_time', width: 180, align: 'center' },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    align: 'center',
    render(row) {
      if (row.is_dir) return '-'
      return h(
        NButton,
        {
          size: 'small',
          type: 'info',
          loading: creatingSharePath.value === row.path,
          disabled: isCreatingShare.value,
          onClick: () => createShare(row),
        },
        { default: () => '创建分享' }
      )
    },
  },
]

onMounted(() => {
  loadFiles()
})

async function loadFiles() {
  try {
    loading.value = true
    const res = await api.webdavList({ path: currentPath.value })
    fileList.value = res.data || []
    await nextTick()
    fileTable.value?.handleSearch()
  } finally {
    loading.value = false
  }
}

async function openDir(path) {
  currentPath.value = path
  await loadFiles()
}

async function goParent() {
  if (currentPath.value === '/') return
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  currentPath.value = parts.length ? '/' + parts.join('/') : '/'
  await loadFiles()
}

async function createShare(row) {
  if (isCreatingShare.value) return
  try {
    creatingSharePath.value = row.path
    const res = await api.webdavCreateShare({
      file_path: row.path,
      file_name: row.name,
      expire_hours: null,
    })
    if (res?.data?.reused) {
      $message.info('该文件已有有效分享，已返回原链接（可在“分享记录”查看）')
    } else {
      $message.success('分享创建成功，可在“分享记录”菜单查看')
    }
  } finally {
    creatingSharePath.value = ''
  }
}
</script>

<template>
  <CommonPage title="外发网盘" show-footer>
    <NCard size="small" title="目录与文件">
      <NSpace vertical>
        <NSpace justify="space-between" align="center">
          <NSpace size="small" align="center" class="path-nav">
            <template v-for="(item, idx) in breadcrumbItems" :key="item.path">
              <NButton
                v-if="idx < breadcrumbItems.length - 1"
                text
                size="small"
                type="primary"
                @click="openDir(item.path)"
              >
                {{ item.label }}
              </NButton>
              <span v-else class="path-current">{{ item.label }}</span>
              <span v-if="idx < breadcrumbItems.length - 1" class="path-sep">/</span>
            </template>
          </NSpace>
        </NSpace>

        <NSpace>
          <NButton tertiary round type="primary" @click="goParent">返回上级</NButton>
          <NButton secondary round type="default" :loading="loading" @click="loadFiles">刷新</NButton>
        </NSpace>

        <CrudTable
          ref="fileTable"
          :columns="fileColumns"
          :is-pagination="false"
          :remote="false"
          :get-data="getFileTableData"
        />
      </NSpace>
    </NCard>
  </CommonPage>
</template>

<style scoped>
.path-nav {
  flex-wrap: wrap;
}

.path-sep {
  color: #9aa0a6;
  user-select: none;
}

.path-current {
  font-weight: 600;
  color: #1f2937;
}
</style>
