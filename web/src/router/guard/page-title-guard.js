import { useAppStore } from '@/store'

export function createPageTitleGuard(router) {
  router.afterEach((to) => {
    const appStore = useAppStore()
    const baseTitle = appStore.siteTitle || import.meta.env.VITE_TITLE
    const pageTitle = to.meta?.title
    if (pageTitle) {
      document.title = `${pageTitle} | ${baseTitle}`
    } else {
      document.title = baseTitle
    }
  })
}
