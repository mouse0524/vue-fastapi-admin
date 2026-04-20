<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Quill from 'quill'
import 'quill/dist/quill.snow.css'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '请输入内容',
  },
  minHeight: {
    type: Number,
    default: 180,
  },
  maxHeight: {
    type: Number,
    default: 420,
  },
})

const emit = defineEmits(['update:modelValue'])

const editorRef = ref(null)
let quill = null
let syncing = false

onMounted(() => {
  if (!editorRef.value) return
  quill = new Quill(editorRef.value, {
    theme: 'snow',
    placeholder: props.placeholder,
    modules: {
      toolbar: [
        [{ header: [1, 2, 3, false] }],
        [{ size: ['small', false, 'large', 'huge'] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ align: [] }],
        [{ list: 'ordered' }, { list: 'bullet' }],
        [{ color: [] }, { background: [] }],
        ['blockquote', 'code-block'],
        ['clean'],
      ],
    },
  })

  quill.root.style.minHeight = `${props.minHeight}px`
  quill.root.style.maxHeight = `${props.maxHeight}px`
  quill.root.style.overflowY = 'auto'
  quill.root.style.boxSizing = 'border-box'
  quill.root.innerHTML = props.modelValue || ''
  quill.on('text-change', () => {
    if (!quill) return
    syncing = true
    emit('update:modelValue', quill.root.innerHTML)
    syncing = false
  })
})

watch(
  () => props.modelValue,
  (val) => {
    if (!quill || syncing) return
    const html = val || ''
    if (quill.root.innerHTML !== html) {
      quill.root.innerHTML = html
    }
  }
)

onBeforeUnmount(() => {
  quill = null
})
</script>

<template>
  <div class="rich-editor-wrap">
    <div ref="editorRef"></div>
  </div>
</template>

<style scoped>
.rich-editor-wrap {
  width: 100%;
}

.rich-editor-wrap :deep(.ql-toolbar.ql-snow) {
  border-radius: 8px 8px 0 0;
  border-color: #d6dde8;
  width: 100%;
}

.rich-editor-wrap :deep(.ql-container.ql-snow) {
  border-radius: 0 0 8px 8px;
  border-color: #d6dde8;
  width: 100%;
}

.rich-editor-wrap :deep(.ql-editor) {
  overflow-y: auto;
}
</style>
