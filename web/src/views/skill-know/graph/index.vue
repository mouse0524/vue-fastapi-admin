<script setup>
import { computed, onMounted, ref } from 'vue'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '知识图谱' })

const loading = ref(false)
const graph = ref({ nodes: [], edges: [] })
const relations = ref([])
const selectedNode = ref(null)
const centerUri = ref('')
const relationFilter = ref('')
const edgeTypeFilter = ref('all')

const nodeMap = computed(() => Object.fromEntries(graph.value.nodes.map((node) => [node.uri, node])))
const selectedRelations = computed(() => {
  if (!selectedNode.value) return relations.value
  return relations.value.filter((item) => item.source_uri === selectedNode.value.uri || item.target_uri === selectedNode.value.uri)
})
const filteredEdges = computed(() => {
  if (edgeTypeFilter.value === 'all') return graph.value.edges || []
  return (graph.value.edges || []).filter((edge) => edge.type === edgeTypeFilter.value)
})

onMounted(loadGraph)

async function loadGraph() {
  loading.value = true
  try {
    const graphParams = { depth: 2, limit: 300 }
    if (centerUri.value.trim()) graphParams.center_uri = centerUri.value.trim()
    const relationParams = { limit: 300 }
    if (relationFilter.value) relationParams.relation_type = relationFilter.value
    const [graphRes, relationRes] = await Promise.all([
      api.skillKnowGraph(graphParams),
      api.skillKnowGraphRelations(relationParams),
    ])
    graph.value = graphRes.data || { nodes: [], edges: [] }
    relations.value = relationRes.data?.items || []
    selectedNode.value = graph.value.nodes[0] || null
  } finally {
    loading.value = false
  }
}

function nodeClass(node) {
  return ['graph-node', node.type, { active: selectedNode.value?.uri === node.uri }]
}

function relationLabel(type) {
  return {
    derived_from: '来源于',
    depends_on: '依赖',
    related_to: '相关',
    merged_from: '合并自',
  }[type] || type
}

function focusNode(uri) {
  centerUri.value = uri
  loadGraph()
}
</script>

<template>
  <CommonPage title="知识图谱" show-footer>
    <div class="sk-theme-page">
    <div class="sk-hero">
      <h2 class="sk-hero-title">知识图谱与溯源关系</h2>
      <p class="sk-hero-sub">查看 Skill 与文档的 derived_from / merged_from / depends_on 等关系，支持中心 URI 聚焦。</p>
    </div>
    <NSpin :show="loading">
      <div class="graph-shell">
        <NCard :bordered="false" class="graph-main">
          <template #header>
            <NSpace justify="space-between" align="center">
              <span>Context Relation 图谱</span>
              <NSpace>
                <NInput v-model:value="centerUri" clearable placeholder="中心 URI，可为空" style="width: 360px" @keyup.enter="loadGraph" />
                <NSelect
                  v-model:value="relationFilter"
                  clearable
                  placeholder="关系类型"
                  style="width: 150px"
                  :options="[
                    { label: '来源于', value: 'derived_from' },
                    { label: '依赖', value: 'depends_on' },
                    { label: '相关', value: 'related_to' },
                    { label: '合并自', value: 'merged_from' },
                  ]"
                />
                <NButton type="primary" @click="loadGraph">刷新</NButton>
              </NSpace>
            </NSpace>
          </template>

          <div class="graph-canvas">
            <div v-if="!graph.nodes.length" class="empty-graph">暂无关系。文档转 Skill 后会自动生成 derived_from 关系。</div>
            <button
              v-for="node in graph.nodes"
              :key="node.uri"
              :class="nodeClass(node)"
              @click="selectedNode = node"
              @dblclick="focusNode(node.uri)"
            >
              <span class="node-type">{{ node.type }}</span>
              <b>{{ node.label }}</b>
              <small>{{ node.uri }}</small>
            </button>
          </div>

          <NCard size="small" title="边列表" class="edge-panel">
            <div class="sk-toolbar-row" style="margin-bottom: 10px">
              <NTag size="small" :type="edgeTypeFilter === 'all' ? 'success' : 'default'" @click="edgeTypeFilter = 'all'" style="cursor:pointer">全部</NTag>
              <NTag size="small" :type="edgeTypeFilter === 'derived_from' ? 'success' : 'default'" @click="edgeTypeFilter = 'derived_from'" style="cursor:pointer">来源</NTag>
              <NTag size="small" :type="edgeTypeFilter === 'merged_from' ? 'success' : 'default'" @click="edgeTypeFilter = 'merged_from'" style="cursor:pointer">合并</NTag>
              <NTag size="small" :type="edgeTypeFilter === 'depends_on' ? 'success' : 'default'" @click="edgeTypeFilter = 'depends_on'" style="cursor:pointer">依赖</NTag>
              <NTag size="small" :type="edgeTypeFilter === 'related_to' ? 'success' : 'default'" @click="edgeTypeFilter = 'related_to'" style="cursor:pointer">相关</NTag>
            </div>
            <div v-for="edge in filteredEdges" :key="edge.id" class="edge-row">
              <NTag size="small" type="info">{{ relationLabel(edge.type) }}</NTag>
              <span>{{ nodeMap[edge.source]?.label || edge.source }}</span>
              <span class="arrow">→</span>
              <span>{{ nodeMap[edge.target]?.label || edge.target }}</span>
              <small>{{ edge.reason }}</small>
            </div>
            <NEmpty v-if="!filteredEdges.length" description="暂无关系边" />
          </NCard>
        </NCard>

        <NCard :bordered="false" class="graph-side" title="节点详情与一跳关系">
          <template v-if="selectedNode">
            <h3>{{ selectedNode.label }}</h3>
            <NTag :type="selectedNode.type === 'skill' ? 'success' : selectedNode.type === 'document' ? 'info' : 'default'">
              {{ selectedNode.type }}
            </NTag>
            <p class="uri">{{ selectedNode.uri }}</p>
            <p>{{ selectedNode.abstract || '暂无摘要' }}</p>
            <NDivider />
            <div v-for="item in selectedRelations" :key="item.id" class="relation-card">
              <NTag size="small">{{ relationLabel(item.relation_type) }}</NTag>
              <div class="relation-line">{{ nodeMap[item.source_uri]?.label || item.source_uri }}</div>
              <div class="relation-line arrow">→</div>
              <div class="relation-line">{{ nodeMap[item.target_uri]?.label || item.target_uri }}</div>
              <p>{{ item.reason || '无原因说明' }}</p>
            </div>
            <NEmpty v-if="!selectedRelations.length" description="该节点暂无一跳关系" />
          </template>
          <NEmpty v-else description="请选择节点" />
        </NCard>
      </div>
    </NSpin>
    </div>
  </CommonPage>
</template>

<style scoped>
.graph-shell { display: grid; grid-template-columns: 1fr 360px; gap: 16px; min-height: calc(100vh - 170px); }
.graph-main, .graph-side { border-radius: 20px; }
.graph-canvas { min-height: 460px; border-radius: 18px; padding: 20px; background: radial-gradient(circle at top left, rgba(24,160,88,.12), transparent 35%), radial-gradient(circle at bottom right, rgba(32,128,240,.12), transparent 35%), rgba(15, 23, 42, .03); display: flex; flex-wrap: wrap; align-content: flex-start; gap: 14px; }
.graph-node { width: 210px; min-height: 112px; text-align: left; border: 1px solid rgba(148,163,184,.25); background: white; border-radius: 16px; padding: 12px; cursor: pointer; box-shadow: 0 10px 24px rgba(15,23,42,.06); transition: .2s; }
.graph-node:hover, .graph-node.active { transform: translateY(-2px); border-color: #18a058; box-shadow: 0 16px 32px rgba(24,160,88,.16); }
.graph-node.skill { background: linear-gradient(135deg, rgba(24,160,88,.14), #fff); border-left: 4px solid #1f9d74; }
.graph-node.document { background: linear-gradient(135deg, rgba(32,128,240,.14), #fff); border-left: 4px solid #2f6feb; }
.graph-node.context { background: linear-gradient(135deg, rgba(100,116,139,.12), #fff); border-left: 4px solid #64748b; }
.node-type { display: inline-block; font-size: 11px; color: #64748b; margin-bottom: 8px; text-transform: uppercase; }
.graph-node b, .graph-node small { display: block; }
.graph-node small, .uri { color: #7b8494; word-break: break-all; }
.edge-panel { margin-top: 16px; }
.edge-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px dashed rgba(148,163,184,.35); flex-wrap: wrap; }
.edge-row small { color: #7b8494; width: 100%; }
.arrow { color: #18a058; font-weight: 700; }
.relation-card { padding: 12px; border-radius: 14px; background: rgba(148,163,184,.08); margin-bottom: 10px; }
.relation-line { margin-top: 6px; word-break: break-word; }
.empty-graph { margin: auto; color: #7b8494; }
@media (max-width: 1100px) { .graph-shell { grid-template-columns: 1fr; } }
</style>
