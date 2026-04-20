<script setup>
import { computed, onMounted, ref } from 'vue'
import { NButton, NForm, NFormItem, NInput, NSelect, NUpload, NAlert, NSpace, NTag } from 'naive-ui'
import { getToken, isNullOrWhitespace } from '@/utils'
import api from '@/api'
import RichTextEditor from '@/components/editor/RichTextEditor.vue'

defineOptions({ name: '提交工单' })

const isAuthed = computed(() => !isNullOrWhitespace(getToken()))
const pageTitle = computed(() => (isAuthed.value ? '提交工单' : '游客工单提交'))
const pageDesc = computed(() =>
  isAuthed.value
    ? '请尽量详细描述问题，客服审核后会转技术处理。'
    : '无需登录即可提交工单，我们会通过你填写的联系方式反馈处理进度。'
)

const formRef = ref(null)
const uploadLoading = ref(false)
const submitting = ref(false)
const captchaImage = ref('')
const uploadedAttachmentIds = ref([])

const form = ref({
  company_name: '',
  contact_name: '',
  email: '',
  phone: '',
  category: '',
  title: '',
  description: '',
  captcha_id: '',
  captcha_code: '',
})

const categoryOptions = ref([
  { label: '登录问题', value: '登录问题' },
  { label: '权限问题', value: '权限问题' },
  { label: '系统异常', value: '系统异常' },
  { label: '其他', value: '其他' },
])

const rules = {
  company_name: { required: true, message: '请输入公司名称', trigger: ['blur', 'input'] },
  contact_name: { required: true, message: '请输入联系人', trigger: ['blur', 'input'] },
  email: { required: true, message: '请输入邮箱', trigger: ['blur', 'input'] },
  phone: { required: true, message: '请输入手机号', trigger: ['blur', 'input'] },
  category: { required: true, message: '请选择分类', trigger: ['change'] },
  title: { required: true, message: '请输入标题', trigger: ['blur', 'input'] },
  description: { required: true, message: '请输入问题描述', trigger: ['blur', 'input'] },
  captcha_code: { required: true, message: '请输入验证码', trigger: ['blur', 'input'] },
}

onMounted(async () => {
  await Promise.all([fetchPublicConfig(), fetchCaptcha()])
  if (isAuthed.value) {
    await fetchPrefill()
  }
})

async function fetchPublicConfig() {
  try {
    const res = await api.getPublicConfig()
    const categories = res.data?.ticket_categories || []
    if (categories.length > 0) {
      categoryOptions.value = categories.map((item) => ({ label: item, value: item }))
      if (!form.value.category) {
        form.value.category = categoryOptions.value[0].value
      }
    }
  } catch (error) {
    console.error('fetchPublicConfig error', error)
  }
}

async function fetchCaptcha() {
  const res = await api.getCaptcha()
  form.value.captcha_id = res.data.captcha_id
  captchaImage.value = `data:image/png;base64,${res.data.image_base64}`
}

async function fetchPrefill() {
  try {
    const res = await api.getTicketPrefill()
    form.value.company_name = res.data?.company_name || form.value.company_name
    form.value.contact_name = res.data?.contact_name || form.value.contact_name
    form.value.email = res.data?.email || form.value.email
    form.value.phone = res.data?.phone || form.value.phone
  } catch (error) {
    console.error('fetchPrefill error', error)
  }
}

function quickFill() {
  fetchPrefill()
}

async function customUpload({ file, onFinish, onError }) {
  try {
    uploadLoading.value = true
    const res = isAuthed.value ? await api.uploadTicketAttachment(file.file) : await api.uploadPublicTicketAttachment(file.file)
    uploadedAttachmentIds.value.push(res.data.id)
    onFinish()
  } catch (error) {
    onError()
  } finally {
    uploadLoading.value = false
  }
}

function handleRemove({ file }) {
  const idx = uploadedAttachmentIds.value.findIndex((id) => id === file.id)
  if (idx >= 0) uploadedAttachmentIds.value.splice(idx, 1)
}

function resetForm() {
  const keepCaptchaId = form.value.captcha_id
  form.value = {
    company_name: '',
    contact_name: '',
    email: '',
    phone: '',
    category: categoryOptions.value[0]?.value || '',
    title: '',
    description: '',
    captcha_id: keepCaptchaId,
    captcha_code: '',
  }
  uploadedAttachmentIds.value = []
}

function submit() {
  formRef.value?.validate(async (err) => {
    if (err) return
    try {
      submitting.value = true
      const payload = {
        ...form.value,
        attachment_ids: uploadedAttachmentIds.value,
      }
      if (isAuthed.value) {
        await api.createTicket(payload)
      } else {
        await api.createPublicTicket(payload)
      }
      $message.success('工单已提交，我们会尽快处理并反馈进度')
      resetForm()
      await fetchCaptcha()
      if (isAuthed.value) {
        await fetchPrefill()
      }
    } catch (error) {
      await fetchCaptcha()
    } finally {
      submitting.value = false
    }
  })
}
</script>

<template>
  <div class="ticket-submit-page">
    <div class="hero">
      <div class="hero-left">
        <h2>{{ pageTitle }}</h2>
        <p>{{ pageDesc }}</p>
        <NSpace>
          <NTag class="hero-tag" :bordered="false">客服审核</NTag>
          <NTag class="hero-tag" :bordered="false">技术处理</NTag>
          <NTag class="hero-tag" :bordered="false">状态可追踪</NTag>
        </NSpace>
      </div>
      <div class="hero-right">
        <div class="orb orb-a"></div>
        <div class="orb orb-b"></div>
      </div>
    </div>

    <div class="form-shell">
      <NAlert type="info" class="mb-16">
        提交后我们将按工单状态推进处理。请确保邮箱和手机号可联系。
      </NAlert>

      <NForm ref="formRef" :model="form" :rules="rules" :label-width="100" label-placement="left">
        <NFormItem label="公司名称" path="company_name">
          <NInput v-model:value="form.company_name" placeholder="请输入公司名称" />
        </NFormItem>
        <NFormItem label="联系人" path="contact_name">
          <div class="row-fill">
            <NInput v-model:value="form.contact_name" placeholder="请输入联系人" />
            <NButton v-if="isAuthed" type="default" @click="quickFill">一键填充</NButton>
          </div>
        </NFormItem>
        <NFormItem label="邮箱" path="email">
          <NInput v-model:value="form.email" placeholder="请输入邮箱" />
        </NFormItem>
        <NFormItem label="手机号" path="phone">
          <NInput v-model:value="form.phone" placeholder="请输入手机号" />
        </NFormItem>
        <NFormItem label="问题分类" path="category">
          <NSelect v-model:value="form.category" :options="categoryOptions" placeholder="请选择分类" />
        </NFormItem>
        <NFormItem label="问题标题" path="title">
          <NInput v-model:value="form.title" placeholder="例如：用户导入报错 500" />
        </NFormItem>
        <NFormItem label="问题描述" path="description">
          <div class="editor-host">
            <RichTextEditor
              v-model="form.description"
              placeholder="建议包含问题现象、复现步骤、影响范围"
              :min-height="220"
              :max-height="460"
            />
          </div>
        </NFormItem>
        <NFormItem label="附件">
          <NUpload :default-upload="false" :custom-request="customUpload" :max="5" @remove="handleRemove">
            <NButton :loading="uploadLoading">上传附件</NButton>
          </NUpload>
        </NFormItem>
        <NFormItem label="验证码" path="captcha_code">
          <div class="captcha-row">
            <NInput v-model:value="form.captcha_code" placeholder="请输入验证码" style="width: 180px" />
            <img :src="captchaImage" alt="captcha" class="captcha-img" @click="fetchCaptcha" />
          </div>
        </NFormItem>
        <NFormItem>
          <NButton class="submit-btn" type="primary" :loading="submitting" @click="submit">提交工单</NButton>
        </NFormItem>
      </NForm>
    </div>
  </div>
</template>

<style scoped>
.ticket-submit-page {
  min-height: calc(100vh - 90px);
  padding: 20px;
  box-sizing: border-box;
  overflow-y: auto;
  max-height: calc(100vh - 90px);
  background:
    radial-gradient(circle at 12% 10%, rgba(244, 81, 30, 0.08), transparent 44%),
    radial-gradient(circle at 88% 20%, rgba(249, 115, 22, 0.07), transparent 42%),
    linear-gradient(180deg, #f5f7fb 0%, #f7f9fc 100%);
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 18px;
  padding: 24px;
  background: linear-gradient(
    130deg,
    color-mix(in srgb, var(--primary-color) 65%, #6b2a13 35%) 0%,
    color-mix(in srgb, var(--primary-color) 58%, #374151 42%) 52%,
    color-mix(in srgb, var(--primary-color-hover) 52%, #ffffff 48%) 100%
  );
  color: #fff;
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.16);
  overflow: hidden;
}

.hero-left h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
}

.hero-left p {
  margin: 10px 0 14px;
  opacity: 0.92;
}

.hero-tag {
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
}

.submit-btn {
  min-width: 120px;
}

.submit-btn :deep(.n-button__border),
.submit-btn :deep(.n-button__state-border) {
  border: none;
}

.submit-btn :deep(.n-button__color) {
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--primary-color) 72%, #7a2a0f 28%) 0%,
    color-mix(in srgb, var(--primary-color) 64%, #374151 36%) 55%,
    color-mix(in srgb, var(--primary-color-hover) 58%, #ffffff 42%) 100%
  );
}

.submit-btn:hover :deep(.n-button__color) {
  filter: brightness(1.02);
}

.hero-right {
  position: relative;
  width: 180px;
  height: 90px;
}

.orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(1px);
}

.orb-a {
  width: 120px;
  height: 120px;
  right: -20px;
  top: -18px;
  background: rgba(255, 255, 255, 0.2);
}

.orb-b {
  width: 70px;
  height: 70px;
  right: 70px;
  top: 34px;
  background: rgba(255, 255, 255, 0.26);
}

.form-shell {
  margin-top: 20px;
  border-radius: 18px;
  padding: 24px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(9, 30, 66, 0.08);
}

.row-fill {
  display: flex;
  gap: 12px;
  width: 100%;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.captcha-img {
  height: 40px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid #e5e7eb;
}

.editor-host {
  width: 100%;
}

@media (max-width: 900px) {
  .ticket-submit-page {
    padding: 12px;
  }

  .hero {
    padding: 18px;
  }

  .hero-right {
    display: none;
  }

  .form-shell {
    padding: 16px;
  }

  .row-fill {
    flex-direction: column;
  }
}
</style>
