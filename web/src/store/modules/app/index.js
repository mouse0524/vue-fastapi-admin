import { defineStore } from 'pinia'
import { useDark } from '@vueuse/core'
import { lStorage } from '@/utils'
import i18n from '~/i18n'

const currentLocale = lStorage.get('locale')
const { locale } = i18n.global

const isDark = useDark()
export const useAppStore = defineStore('app', {
  state() {
    return {
      collapsed: false,
      fullScreen: true,
      /** keepAlive路由的key，重新赋值可重置keepAlive */
      aliveKeys: {},
      isDark,
      locale: currentLocale || 'en',
      siteTitle: import.meta.env.VITE_TITLE || 'Vue FastAPI Admin',
      siteLogo: '',
      allowPartnerRegister: true,
      ticketCategories: ['登录问题', '权限问题', '系统异常', '其他'],
    }
  },
  actions: {
    async reloadPage() {
      document.documentElement.scrollTo({ left: 0, top: 0 })
    },
    switchCollapsed() {
      this.collapsed = !this.collapsed
    },
    setCollapsed(collapsed) {
      this.collapsed = collapsed
    },
    setFullScreen(fullScreen) {
      this.fullScreen = fullScreen
    },
    setAliveKeys(key, val) {
      this.aliveKeys[key] = val
    },
    /** 设置暗黑模式 */
    setDark(isDark) {
      this.isDark = isDark
    },
    /** 切换/关闭 暗黑模式 */
    toggleDark() {
      this.isDark = !this.isDark
    },
    setLocale(newLocale) {
      this.locale = newLocale
      locale.value = newLocale
      lStorage.set('locale', newLocale)
    },
    setSiteConfig(config = {}) {
      this.siteTitle = config.site_title || this.siteTitle
      this.siteLogo = config.site_logo || ''
      this.allowPartnerRegister =
        typeof config.allow_partner_register === 'boolean' ? config.allow_partner_register : this.allowPartnerRegister
      if (Array.isArray(config.ticket_categories) && config.ticket_categories.length > 0) {
        this.ticketCategories = config.ticket_categories
      }
    },
  },
})
