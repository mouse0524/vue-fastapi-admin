<script setup>
import { onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDivider,
  NDynamicTags,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSwitch,
  NTabPane,
  NTabs,
  NUpload,
} from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import { useAppStore } from '@/store'

defineOptions({ name: '系统设置' })

const formRef = ref(null)
const loading = ref(false)
const saving = ref(false)
const webdavTesting = ref(false)
const llmTesting = ref(false)
const logoUploading = ref(false)
const previewVisible = ref(false)
const appStore = useAppStore()
const form = ref({
  site_title: 'Vue FastAPI Admin',
  site_logo: '',
  allow_partner_register: true,
  ticket_categories: ['登录问题', '权限问题', '系统异常', '其他'],
  ticket_root_causes: ['代码缺陷', '配置错误', '环境异常', '数据问题', '操作不当', '第三方依赖'],
  smtp_host: '',
  smtp_port: 465,
  smtp_username: '',
  smtp_password: '',
  smtp_sender: '',
  smtp_sender_name: '系统通知',
  smtp_use_tls: false,
  smtp_use_ssl: true,
  email_verify_subject: '代理商注册验证码',
  email_verify_is_html: true,
  email_verify_template: '您好，您的验证码是：{code}，{minutes}分钟内有效。',
  register_review_approve_subject: '注册审核结果通知',
  register_review_approve_is_html: true,
  register_review_approve_template: '您好，{contact_name}，您的{register_type}注册申请已审核通过，现可使用邮箱登录系统。',
  register_review_reject_subject: '注册审核结果通知',
  register_review_reject_is_html: true,
  register_review_reject_template: '您好，{contact_name}，您的{register_type}注册申请已驳回。驳回理由：{reason}',
  webdav_enabled: false,
  webdav_base_url: '',
  webdav_username: '',
  webdav_password: '',
  webdav_share_default_expire_hours: 168,
  webdav_signature_secret: '',
  llm_provider: 'openai',
  llm_base_url: 'https://api.openai.com/v1',
  llm_api_key: '',
  llm_model: 'mock-rag-v1',
  llm_timeout_seconds: 20,
})

const previewParams = ref({
  contact_name: '张三',
  register_type: '用户',
  reason: '资料不完整，请补充设备机器码',
  code: '123456',
  minutes: 10,
})

const presetTemplates = {
  verifySubject: '【系统通知】邮箱验证码',
  verifyHtml: `
<div style="font-family:Arial,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#1f2937;line-height:1.7;">
  <h2 style="margin:0 0 12px;font-size:18px;color:#0f4c81;">邮箱验证码</h2>
  <p style="margin:0 0 10px;">您好，验证码用于本次注册校验：</p>
  <div style="display:inline-block;padding:10px 18px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;font-size:24px;font-weight:700;letter-spacing:4px;color:#1d4ed8;">{code}</div>
  <p style="margin:12px 0 0;color:#6b7280;">验证码 {minutes} 分钟内有效，请勿泄露给他人。</p>
</div>
`.trim(),
  approveSubject: '【系统通知】注册审核通过',
  approveHtml: `
<div style="font-family:Arial,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#1f2937;line-height:1.7;">
  <h2 style="margin:0 0 12px;font-size:18px;color:#15803d;">注册审核通过</h2>
  <p style="margin:0 0 8px;">您好，<b>{contact_name}</b>：</p>
  <p style="margin:0 0 8px;">您提交的 <b>{register_type}</b> 注册申请已审核通过。</p>
  <p style="margin:0;color:#374151;">现在可使用注册邮箱登录系统并提交工单。</p>
</div>
`.trim(),
  rejectSubject: '【系统通知】注册审核驳回',
  rejectHtml: `
<div style="font-family:Arial,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#1f2937;line-height:1.7;">
  <h2 style="margin:0 0 12px;font-size:18px;color:#b91c1c;">注册审核驳回</h2>
  <p style="margin:0 0 8px;">您好，<b>{contact_name}</b>：</p>
  <p style="margin:0 0 8px;">您提交的 <b>{register_type}</b> 注册申请未通过审核。</p>
  <p style="margin:0 0 8px;">驳回理由：<span style="color:#b91c1c;font-weight:600;">{reason}</span></p>
  <p style="margin:0;color:#6b7280;">请根据提示完善信息后重新提交。</p>
</div>
`.trim(),
}

const rules = {
  site_title: { required: true, message: '请输入网站标题', trigger: ['input', 'blur'] },
  ticket_categories: {
    required: true,
    validator: () => {
      if (!form.value.ticket_categories || form.value.ticket_categories.length === 0) {
        return new Error('请至少配置一个工单分类')
      }
      return true
    },
    trigger: ['change', 'blur'],
  },
}

onMounted(() => {
  loadData()
})

async function loadData() {
  try {
    loading.value = true
    const res = await api.getSystemSettings()
    form.value = {
      ...form.value,
      ...res.data,
      ticket_categories: res.data?.ticket_categories?.length
        ? res.data.ticket_categories
        : form.value.ticket_categories,
    }
    const publicRes = await api.getPublicConfig()
    appStore.setSiteConfig(publicRes.data || {})
  } finally {
    loading.value = false
  }
}

function save() {
  formRef.value?.validate(async (err) => {
    if (err) return
    try {
      saving.value = true
      await api.updateSystemSettings(form.value)
      $message.success('设置已保存并生效')
      const publicRes = await api.getPublicConfig()
      appStore.setSiteConfig(publicRes.data || {})
      await loadData()
    } finally {
      saving.value = false
    }
  })
}

async function testWebdavConnection() {
  try {
    webdavTesting.value = true
    const res = await api.testWebdavConnection({
      webdav_enabled: form.value.webdav_enabled,
      webdav_base_url: form.value.webdav_base_url,
      webdav_username: form.value.webdav_username,
      webdav_password: form.value.webdav_password,
    })
    $message.success(res?.msg || 'WebDAV连接成功')
  } finally {
    webdavTesting.value = false
  }
}

async function testLlmConnection() {
  try {
    llmTesting.value = true
    const res = await api.kbLlmTest()
    const data = res?.data || {}
    if (data.ok) {
      $message.success(`模型连接成功（${data.provider || '-'} / ${data.model || '-'}，${data.latency_ms ?? '-'}ms）`)
    } else {
      $message.warning(`模型连接失败：${data.error_code || 'unknown_error'}`)
    }
  } finally {
    llmTesting.value = false
  }
}

async function uploadLogo({ file, onFinish, onError }) {
  try {
    logoUploading.value = true
    await api.uploadSiteLogo(file.file)
    const publicRes = await api.getPublicConfig()
    appStore.setSiteConfig(publicRes.data || {})
    const res = await api.getSystemSettings()
    form.value.site_logo = res.data?.site_logo || ''
    $message.success('Logo已上传并更新')
    onFinish()
  } catch (error) {
    onError()
  } finally {
    logoUploading.value = false
  }
}

function renderTemplate(template, params) {
  let content = template || ''
  Object.keys(params).forEach((key) => {
    content = content.replaceAll(`{${key}}`, params[key])
  })
  return content
}

function openPreview() {
  previewVisible.value = true
}

function applyPresetHtmlTemplates() {
  form.value.email_verify_subject = presetTemplates.verifySubject
  form.value.email_verify_template = presetTemplates.verifyHtml
  form.value.email_verify_is_html = true

  form.value.register_review_approve_subject = presetTemplates.approveSubject
  form.value.register_review_approve_template = presetTemplates.approveHtml
  form.value.register_review_approve_is_html = true

  form.value.register_review_reject_subject = presetTemplates.rejectSubject
  form.value.register_review_reject_template = presetTemplates.rejectHtml
  form.value.register_review_reject_is_html = true

  $message.success('推荐模板已应用，请保存后生效')
}
</script>

<template>
  <CommonPage title="系统设置" show-footer>
    <n-spin :show="loading">
      <NForm ref="formRef" :model="form" :rules="rules" :label-width="120" label-placement="left">
        <NTabs type="line" animated>
          <NTabPane name="site" tab="站点配置">
            <NCard size="small" title="基础信息">
              <NFormItem label="网站标题" path="site_title">
                <NInput v-model:value="form.site_title" placeholder="请输入网站标题" />
              </NFormItem>
              <NFormItem label="网站Logo" path="site_logo">
                <div flex items-center gap-12>
                  <NUpload :default-upload="false" :custom-request="uploadLogo" :max="1" accept=".jpg,.jpeg,.png,.webp,.svg">
                    <NButton :loading="logoUploading">上传本地Logo</NButton>
                  </NUpload>
                  <img v-if="appStore.siteLogo" :src="appStore.siteLogo" alt="logo" style="height: 36px; width: 36px" />
                </div>
              </NFormItem>
              <NFormItem label="开放注册">
                <NSwitch v-model:value="form.allow_partner_register" />
              </NFormItem>
            </NCard>
          </NTabPane>

          <NTabPane name="ticket" tab="工单配置">
            <NCard size="small" title="工单分类">
              <NFormItem label="问题分类" path="ticket_categories">
                <NDynamicTags v-model:value="form.ticket_categories" />
              </NFormItem>
              <NFormItem label="问题根因" path="ticket_root_causes">
                <NDynamicTags v-model:value="form.ticket_root_causes" />
              </NFormItem>
            </NCard>
          </NTabPane>

          <NTabPane name="mail" tab="发件配置">
            <NCard size="small" title="SMTP设置">
              <NFormItem label="SMTP主机">
                <NInput v-model:value="form.smtp_host" placeholder="例如 smtp.qq.com" />
              </NFormItem>
              <NFormItem label="SMTP端口">
                <NInputNumber v-model:value="form.smtp_port" :min="1" :max="65535" />
              </NFormItem>
              <NFormItem label="SMTP用户名">
                <NInput v-model:value="form.smtp_username" placeholder="可选，默认使用发件邮箱" />
              </NFormItem>
              <NFormItem label="SMTP密码">
                <NInput v-model:value="form.smtp_password" type="password" show-password-on="mousedown" />
              </NFormItem>
              <NFormItem label="发件邮箱">
                <NInput v-model:value="form.smtp_sender" placeholder="例如 xxx@qq.com" />
              </NFormItem>
              <NFormItem label="发件人名称">
                <NInput v-model:value="form.smtp_sender_name" placeholder="系统通知" />
              </NFormItem>
              <NFormItem label="启用TLS">
                <NSwitch v-model:value="form.smtp_use_tls" />
              </NFormItem>
              <NFormItem label="启用SSL">
                <NSwitch v-model:value="form.smtp_use_ssl" />
              </NFormItem>
            </NCard>
          </NTabPane>

          <NTabPane name="webdav" tab="WebDAV管理">
            <NCard size="small" title="WebDAV统一配置">
              <NAlert type="info" class="mb-12">
                这里统一维护外发网盘 WebDAV 配置；密码显示为掩码，保持不变可直接保存。
              </NAlert>
              <NFormItem label="启用WebDAV">
                <NSwitch v-model:value="form.webdav_enabled" />
              </NFormItem>
              <NFormItem label="Base URL">
                <NInput v-model:value="form.webdav_base_url" placeholder="例如 https://webdav.example.com/webdav" />
              </NFormItem>
              <NFormItem label="用户名">
                <NInput v-model:value="form.webdav_username" placeholder="请输入WebDAV用户名" />
              </NFormItem>
              <NFormItem label="密码">
                <NInput
                  v-model:value="form.webdav_password"
                  type="password"
                  show-password-on="mousedown"
                  placeholder="保持不变可留******"
                />
              </NFormItem>
              <NFormItem label="默认分享时长(小时)">
                <NInputNumber v-model:value="form.webdav_share_default_expire_hours" :min="1" :max="8760" />
              </NFormItem>
              <NFormItem label="签名密钥">
                <NInput v-model:value="form.webdav_signature_secret" placeholder="用于外链签名校验（可选）" />
              </NFormItem>
              <NFormItem>
                <NButton type="primary" ghost :loading="webdavTesting" @click="testWebdavConnection">测试连接</NButton>
              </NFormItem>
            </NCard>
          </NTabPane>

          <NTabPane name="llm" tab="AI模型配置">
            <NCard size="small" title="大模型统一配置">
              <NAlert type="info" class="mb-12">
                知识库问答会优先读取这里的模型配置；API Key 显示为掩码，保持不变可直接保存。
              </NAlert>
              <NFormItem label="提供商">
                <NInput v-model:value="form.llm_provider" placeholder="例如 openai / openai_compat" />
              </NFormItem>
              <NFormItem label="Base URL">
                <NInput v-model:value="form.llm_base_url" placeholder="例如 https://api.openai.com/v1" />
              </NFormItem>
              <NFormItem label="API Key">
                <NInput
                  v-model:value="form.llm_api_key"
                  type="password"
                  show-password-on="mousedown"
                  placeholder="保持不变可留******"
                />
              </NFormItem>
              <NFormItem label="模型名称">
                <NInput v-model:value="form.llm_model" placeholder="例如 gpt-4o-mini" />
              </NFormItem>
              <NFormItem label="超时(秒)">
                <NInputNumber v-model:value="form.llm_timeout_seconds" :min="1" :max="120" />
              </NFormItem>
              <NFormItem>
                <NButton type="primary" ghost :loading="llmTesting" @click="testLlmConnection">测试连接</NButton>
              </NFormItem>
            </NCard>
          </NTabPane>

          <NTabPane name="template" tab="邮件模板">
            <NAlert type="info" class="mb-12">
              验证码模板支持变量：{code}、{minutes}；审核模板支持变量：{contact_name}、{register_type}、{reason}
            </NAlert>
            <div class="mb-12" flex items-center gap-12>
              <NButton type="primary" ghost @click="applyPresetHtmlTemplates">一键应用推荐HTML模板</NButton>
              <NButton type="default" @click="openPreview">预览模板效果</NButton>
            </div>

            <NCard size="small" title="验证码邮件模板" class="mb-12">
              <NFormItem label="邮件标题">
                <NInput v-model:value="form.email_verify_subject" />
              </NFormItem>
              <NFormItem label="HTML格式">
                <NSwitch v-model:value="form.email_verify_is_html" />
              </NFormItem>
              <NFormItem label="邮件模板">
                <NInput
                  v-model:value="form.email_verify_template"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 8 }"
                  placeholder="支持变量 {code}、{minutes}"
                />
              </NFormItem>
            </NCard>

            <NCard size="small" title="注册审核通知模板">
              <NFormItem label="通过标题">
                <NInput v-model:value="form.register_review_approve_subject" />
              </NFormItem>
              <NFormItem label="通过HTML格式">
                <NSwitch v-model:value="form.register_review_approve_is_html" />
              </NFormItem>
              <NFormItem label="通过模板">
                <NInput
                  v-model:value="form.register_review_approve_template"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 8 }"
                />
              </NFormItem>
              <NFormItem label="驳回标题">
                <NInput v-model:value="form.register_review_reject_subject" />
              </NFormItem>
              <NFormItem label="驳回HTML格式">
                <NSwitch v-model:value="form.register_review_reject_is_html" />
              </NFormItem>
              <NFormItem label="驳回模板">
                <NInput
                  v-model:value="form.register_review_reject_template"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 8 }"
                />
              </NFormItem>
            </NCard>
          </NTabPane>
        </NTabs>

        <NFormItem class="mt-16">
          <NButton type="primary" :loading="saving" @click="save">保存设置</NButton>
        </NFormItem>
      </NForm>

      <NModal v-model:show="previewVisible" preset="card" title="模板预览" style="width: 760px">
        <NAlert type="info" class="mb-12">
          预览使用示例变量：姓名=张三、注册类型=用户、驳回理由=资料不完整、验证码=123456、分钟=10。
        </NAlert>

        <NDivider title-placement="left">验证码邮件</NDivider>
        <NFormItem label="标题">
          <NInput :value="form.email_verify_subject" readonly />
        </NFormItem>
        <NFormItem label="HTML格式">
          <NSwitch :value="form.email_verify_is_html" disabled />
        </NFormItem>
        <NFormItem label="内容">
          <NInput
            v-if="!form.email_verify_is_html"
            type="textarea"
            :value="renderTemplate(form.email_verify_template, previewParams)"
            :autosize="{ minRows: 3, maxRows: 6 }"
            readonly
          />
          <div v-else class="preview-html" v-html="renderTemplate(form.email_verify_template, previewParams)"></div>
        </NFormItem>

        <NDivider title-placement="left">审核通过通知</NDivider>
        <NFormItem label="标题">
          <NInput :value="form.register_review_approve_subject" readonly />
        </NFormItem>
        <NFormItem label="HTML格式">
          <NSwitch :value="form.register_review_approve_is_html" disabled />
        </NFormItem>
        <NFormItem label="内容">
          <NInput
            v-if="!form.register_review_approve_is_html"
            type="textarea"
            :value="renderTemplate(form.register_review_approve_template, previewParams)"
            :autosize="{ minRows: 3, maxRows: 6 }"
            readonly
          />
          <div v-else class="preview-html" v-html="renderTemplate(form.register_review_approve_template, previewParams)"></div>
        </NFormItem>

        <NDivider title-placement="left">审核驳回通知</NDivider>
        <NFormItem label="标题">
          <NInput :value="form.register_review_reject_subject" readonly />
        </NFormItem>
        <NFormItem label="HTML格式">
          <NSwitch :value="form.register_review_reject_is_html" disabled />
        </NFormItem>
        <NFormItem label="内容">
          <NInput
            v-if="!form.register_review_reject_is_html"
            type="textarea"
            :value="renderTemplate(form.register_review_reject_template, previewParams)"
            :autosize="{ minRows: 3, maxRows: 6 }"
            readonly
          />
          <div v-else class="preview-html" v-html="renderTemplate(form.register_review_reject_template, previewParams)"></div>
        </NFormItem>
      </NModal>
    </n-spin>
  </CommonPage>
</template>

<style scoped>
.preview-html {
  width: 100%;
  min-height: 80px;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
}
</style>
