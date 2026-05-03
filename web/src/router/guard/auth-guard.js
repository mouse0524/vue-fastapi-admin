import { getToken, isNullOrWhitespace } from '@/utils'
import { useUserStore } from '@/store'

const WHITE_LIST = ['/login', '/404', '/ticket/public-submit']
export function createAuthGuard(router) {
  router.beforeEach(async (to) => {
    const token = getToken()

    /** 没有token的情况 */
    if (isNullOrWhitespace(token)) {
      if (WHITE_LIST.includes(to.path)) return true
      return { path: '/login', query: { ...to.query, redirect: to.path } }
    }

    /** 有token的情况 */
    if (to.path === '/login') return { path: '/' }

    const userStore = useUserStore()
    const roleNames = (userStore.role || []).map((item) => item?.name).filter(Boolean)
    if (!userStore.isSuperUser && to.path.startsWith('/workbench')) {
      if (roleNames.includes('客服')) return { path: '/ticket/review' }
      if (roleNames.includes('技术')) return { path: '/ticket/tech' }
      return { path: '/ticket/my' }
    }

    return true
  })
}
