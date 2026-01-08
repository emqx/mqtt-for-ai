import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import './custom.css'
import { createGtm } from '@gtm-support/vue-gtm'
import NotFound from './components/NotFound.vue'

const theme: Theme = {
  extends: DefaultTheme,
  Layout: () => {
    return h(DefaultTheme.Layout, null, {
      'not-found': () => h(NotFound),
    })
  },
  enhanceApp({ app, router }) {
    // Add Google Tag Manager
    const gtm = createGtm({
      id: 'GTM-MPG87C5',
      enabled: import.meta.env.PROD,
      debug: false,
    })
    app.use(gtm)

    router.onBeforePageLoad = (to: string) => {
      if (!import.meta.env.SSR && window) {
        window.dataLayer = window.dataLayer || []
        setTimeout(() => {
          window.dataLayer!.push({
            event: 'pageView',
            pageType: 'PageView',
            pageUrl: to,
            pageTitle: document.title,
          })
        }, 1000)
      }
    }
  },
}

export default theme
