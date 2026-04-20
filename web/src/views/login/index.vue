<template>
  <AppPage :show-footer="true" bg-cover :style="{ backgroundImage: `url(${bgImg})` }">
    <div
      style="transform: translateY(25px)"
      class="m-auto max-w-1500 min-w-345 f-c-c rounded-10 bg-white bg-opacity-60 p-15 card-shadow"
      dark:bg-dark
    >
      <div hidden w-380 px-20 py-35 md:block>
        <icon-custom-front-page pt-10 text-300 color-primary></icon-custom-front-page>
      </div>

      <div w-320 flex-col px-20 py-35>
        <h5 f-c-c text-24 font-normal color="#6a6a6a">
          <icon-custom-logo mr-10 text-50 color-primary />{{ $t('app_name') }}
        </h5>
        <div mt-30>
          <n-input
            v-model:value="loginInfo.username"
            autofocus
            class="h-50 items-center pl-10 text-16"
            placeholder="请输入邮箱"
            :maxlength="20"
          />
        </div>
        <div mt-30>
          <n-input
            v-model:value="loginInfo.password"
            class="h-50 items-center pl-10 text-16"
            type="password"
            show-password-on="mousedown"
            placeholder="123456"
            :maxlength="20"
            @keypress.enter="handleLogin"
          />
        </div>
        <div mt-30>
          <div flex items-center gap-12>
            <n-input
              v-model:value="loginInfo.captcha_code"
              class="h-50 items-center pl-10 text-16"
              placeholder="请输入登录验证码"
              :maxlength="6"
              @keypress.enter="handleLogin"
            />
            <img :src="loginCaptchaImage" alt="login-captcha" style="height: 40px; cursor: pointer" @click="fetchLoginCaptcha" />
          </div>
        </div>

        <div mt-20>
          <n-button
            h-50
            w-full
            rounded-5
            text-16
            type="primary"
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t('views.login.text_login') }}
          </n-button>
        </div>
        <div mt-12 text-center>
          <n-button v-if="appStore.allowPartnerRegister" text type="primary" @click="showPartnerModal = true">注册账号</n-button>
        </div>
      </div>
    </div>

    <n-modal v-model:show="showPartnerModal" preset="card" title="账号注册" style="width: 520px">
      <n-form ref="partnerFormRef" :model="partnerForm" :rules="partnerRules" label-width="90" label-placement="left">
        <n-form-item label="注册类型">
          <div flex items-center gap-12>
            <n-button
              :type="partnerForm.register_type === 'channel' ? 'primary' : 'default'"
              @click="partnerForm.register_type = 'channel'"
            >
              渠道商注册
            </n-button>
            <n-button :type="partnerForm.register_type === 'user' ? 'primary' : 'default'" @click="partnerForm.register_type = 'user'">
              用户注册
            </n-button>
          </div>
        </n-form-item>
        <n-form-item label="公司名称" path="company_name">
          <n-input v-model:value="partnerForm.company_name" />
        </n-form-item>
        <n-form-item label="联系人" path="contact_name">
          <n-input v-model:value="partnerForm.contact_name" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="partnerForm.email" />
        </n-form-item>
        <n-form-item label="邮箱验证码" path="email_code">
          <div flex items-center gap-12>
            <n-input v-model:value="partnerForm.email_code" style="width: 180px" />
            <n-button :loading="emailCodeSending" :disabled="!canSendEmailCode" @click="openCaptchaModal">{{ emailCodeButtonText }}</n-button>
          </div>
        </n-form-item>
        <n-form-item label="手机号" path="phone">
          <n-input v-model:value="partnerForm.phone" />
        </n-form-item>
        <n-form-item v-if="partnerForm.register_type === 'user'" path="hardware_id" required>
          <template #label>
            <div flex items-center gap-4>
              <span>设备机器码</span>
              <n-tooltip trigger="hover">
                <template #trigger>
                  <icon-mdi:help-circle-outline text-15 color="#999" style="cursor: pointer" />
                </template>
                使用sysadmin登录系统，点击授权-更新应用授权
              </n-tooltip>
            </div>
          </template>
          <n-input v-model:value="partnerForm.hardware_id" placeholder="请输入设备机器码" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input v-model:value="partnerForm.password" type="password" />
        </n-form-item>
      </n-form>
      <div mt-8 flex items-center justify-center gap-6 text-center text-14 font-700 color="#d03050">
        <icon-mdi:phone-in-talk-outline text-16 />
        <span>审核会在24h内完成，如您遇到紧急问题，请拨打 4001381063</span>
      </div>
      <template #footer>
        <div flex justify-end>
          <n-button @click="showPartnerModal = false">取消</n-button>
          <n-button ml-12 type="primary" :loading="partnerSubmitting" @click="submitPartnerRegister">提交注册</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="showCaptchaModal" preset="card" title="图形验证码" style="width: 420px">
      <n-form :model="partnerForm" :rules="captchaRules" label-width="80" label-placement="left">
        <n-form-item label="验证码" path="captcha_code">
          <div flex items-center gap-12>
            <n-input v-model:value="partnerForm.captcha_code" style="width: 180px" placeholder="请输入图形验证码" />
            <img :src="partnerCaptchaImage" style="height: 40px; cursor: pointer" @click="fetchPartnerCaptcha" />
          </div>
        </n-form-item>
      </n-form>
      <template #footer>
        <div flex justify-end>
          <n-button @click="showCaptchaModal = false">取消</n-button>
          <n-button ml-12 type="primary" :loading="emailCodeSending" @click="sendEmailCode">确定发送</n-button>
        </div>
      </template>
    </n-modal>
  </AppPage>
</template>

<script setup>
import { lStorage, setToken } from '@/utils'
import bgImg from '@/assets/images/login_bg.webp'
import api from '@/api'
import { addDynamicRoutes } from '@/router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/store'

const router = useRouter()
const { query } = useRoute()
const { t } = useI18n({ useScope: 'global' })
const appStore = useAppStore()

const loginInfo = ref({
  username: '',
  password: '',
  captcha_id: '',
  captcha_code: '',
})

const loginCaptchaImage = ref('')

const showPartnerModal = ref(false)
const showCaptchaModal = ref(false)
const partnerSubmitting = ref(false)
const emailCodeSending = ref(false)
const emailCodeCooldown = ref(0)
let emailCodeTimer = null
const partnerFormRef = ref(null)
const partnerCaptchaImage = ref('')
const partnerForm = ref({
  register_type: 'channel',
  company_name: '',
  contact_name: '',
  email: '',
  phone: '',
  hardware_id: '',
  password: '',
  email_code: '',
  captcha_id: '',
  captcha_code: '',
})

const partnerRules = {
  company_name: { required: true, message: '请输入公司名称', trigger: ['blur', 'input'] },
  contact_name: { required: true, message: '请输入联系人', trigger: ['blur', 'input'] },
  email: { required: true, message: '请输入邮箱', trigger: ['blur', 'input'] },
  email_code: { required: true, message: '请输入邮箱验证码', trigger: ['blur', 'input'] },
  phone: { required: true, message: '请输入手机号', trigger: ['blur', 'input'] },
  hardware_id: {
    validator: () => {
      if (partnerForm.value.register_type === 'user' && !partnerForm.value.hardware_id?.trim()) {
        return new Error('用户注册必须填写设备机器码')
      }
      return true
    },
    trigger: ['blur', 'input', 'change'],
  },
  password: { required: true, message: '请输入密码', trigger: ['blur', 'input'] },
  captcha_code: { required: true, message: '请输入验证码', trigger: ['blur', 'input'] },
}

const captchaRules = {
  captcha_code: { required: true, message: '请输入图形验证码', trigger: ['blur', 'input'] },
}

const canSendEmailCode = computed(() => {
  return !!partnerForm.value.email?.trim() && !emailCodeSending.value && emailCodeCooldown.value === 0
})

const emailCodeButtonText = computed(() => {
  return emailCodeCooldown.value > 0 ? `${emailCodeCooldown.value}s后重试` : '发送验证码'
})

initLoginInfo()
fetchPublicConfig()
fetchLoginCaptcha()

function initLoginInfo() {
  const localLoginInfo = lStorage.get('loginInfo')
  if (localLoginInfo) {
    loginInfo.value.username = localLoginInfo.username || ''
    loginInfo.value.password = localLoginInfo.password || ''
  }
}

const loading = ref(false)
async function handleLogin() {
  const { username, password } = loginInfo.value
  const captchaCode = loginInfo.value.captcha_code?.trim()
  if (!username || !password || !captchaCode) {
    $message.warning('请输入用户名、密码和验证码')
    return
  }
  if (!loginInfo.value.captcha_id) {
    await fetchLoginCaptcha()
    $message.warning('验证码已刷新，请重新输入')
    return
  }
  try {
    loading.value = true
    $message.loading(t('views.login.message_verifying'))
    const res = await api.login({
      username,
      password: password.toString(),
      captcha_id: loginInfo.value.captcha_id,
      captcha_code: captchaCode,
    })
    $message.success(t('views.login.message_login_success'))
    setToken(res.data.access_token)
    await addDynamicRoutes()
    if (query.redirect) {
      const path = query.redirect
      console.log('path', { path, query })
      Reflect.deleteProperty(query, 'redirect')
      router.push({ path, query })
    } else {
      router.push('/')
    }
  } catch (e) {
    console.error('login error', e.error)
    await fetchLoginCaptcha()
    loginInfo.value.captcha_code = ''
  }
  loading.value = false
}

async function fetchLoginCaptcha() {
  const res = await api.getCaptcha()
  loginInfo.value.captcha_id = res.data.captcha_id
  loginCaptchaImage.value = `data:image/png;base64,${res.data.image_base64}`
}

async function fetchPartnerCaptcha() {
  const res = await api.getCaptcha()
  partnerForm.value.captcha_id = res.data.captcha_id
  partnerCaptchaImage.value = `data:image/png;base64,${res.data.image_base64}`
}

async function fetchPublicConfig() {
  try {
    const res = await api.getPublicConfig()
    appStore.setSiteConfig(res.data || {})
  } catch (error) {
    console.error('fetchPublicConfig error', error)
  }
}

watch(showPartnerModal, async (v) => {
  if (v) {
    await fetchPartnerCaptcha()
  } else {
    resetPartnerRegisterState()
  }
})

function submitPartnerRegister() {
  partnerFormRef.value?.validate(async (err) => {
    if (err) return
    try {
      partnerSubmitting.value = true
      if (partnerForm.value.register_type === 'user') {
        await api.userRegister(partnerForm.value)
      } else {
        await api.channelRegister(partnerForm.value)
      }
      $message.success('注册成功，请等待审核')
      showPartnerModal.value = false
    } catch (error) {
      await fetchPartnerCaptcha()
    } finally {
      partnerSubmitting.value = false
    }
  })
}

async function openCaptchaModal() {
  if (!partnerForm.value.email?.trim()) {
    $message.warning('请先输入邮箱')
    return
  }
  partnerForm.value.captcha_code = ''
  await fetchPartnerCaptcha()
  showCaptchaModal.value = true
}

async function sendEmailCode() {
  const email = partnerForm.value.email?.trim()
  const captchaCode = partnerForm.value.captcha_code?.trim()
  const captchaId = partnerForm.value.captcha_id

  if (!email) {
    $message.warning('请先输入邮箱')
    return
  }
  if (!captchaId) {
    await fetchPartnerCaptcha()
    $message.warning('验证码已刷新，请先输入图形验证码')
    return
  }
  if (!captchaCode) {
    $message.warning('请先输入图形验证码后再发送邮箱验证码')
    return
  }
  try {
    emailCodeSending.value = true
    await api.sendEmailCode({
      email,
      captcha_id: captchaId,
      captcha_code: captchaCode,
    })
    $message.success('邮箱验证码已发送')
    showCaptchaModal.value = false
    startEmailCooldown()
    await fetchPartnerCaptcha()
  } catch (error) {
    await fetchPartnerCaptcha()
  } finally {
    emailCodeSending.value = false
  }
}

function startEmailCooldown(seconds = 60) {
  emailCodeCooldown.value = seconds
  if (emailCodeTimer) {
    clearInterval(emailCodeTimer)
  }
  emailCodeTimer = setInterval(() => {
    if (emailCodeCooldown.value <= 1) {
      emailCodeCooldown.value = 0
      clearInterval(emailCodeTimer)
      emailCodeTimer = null
      return
    }
    emailCodeCooldown.value -= 1
  }, 1000)
}

onBeforeUnmount(() => {
  resetEmailCooldown()
})

function resetEmailCooldown() {
  if (emailCodeTimer) {
    clearInterval(emailCodeTimer)
    emailCodeTimer = null
  }
  emailCodeCooldown.value = 0
}

function resetPartnerRegisterState() {
  showCaptchaModal.value = false
  partnerSubmitting.value = false
  emailCodeSending.value = false
  partnerCaptchaImage.value = ''
  partnerForm.value = {
    register_type: 'channel',
    company_name: '',
    contact_name: '',
    email: '',
    phone: '',
    hardware_id: '',
    password: '',
    email_code: '',
    captcha_id: '',
    captcha_code: '',
  }
  resetEmailCooldown()
}
</script>
