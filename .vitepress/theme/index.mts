import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import './custom.css'
import { createGtm } from '@gtm-support/vue-gtm'
// import giscusTalk from 'vitepress-plugin-comment-with-giscus'
// import { useData, useRoute } from 'vitepress'
// import { toRefs } from 'vue'

const theme: Theme = {
  extends: DefaultTheme,
  enhanceApp({ app, router }) {
    // Add Google Tag Manager
    const gtm = createGtm({
      id: 'GTM-K4TZSNJP',
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
  setup() {
    // const { frontmatter } = toRefs(useData())
    // const route = useRoute()
    // giscusTalk(
    //   {
    //     repo: 'emqx/mcp-over-mqtt-site',
    //     repoId: 'R_kgDOOMOVMQ',
    //     category: 'Announcements',
    //     categoryId: 'DIC_kwDOOMOVMc4CoTsh',
    //     mapping: 'pathname',
    //     inputPosition: 'top',
    //     lang: 'en',
    //     theme: 'preferred_color_scheme',
    //     lightTheme: 'light',
    //     darkTheme: 'transparent_dark',
    //   },
    //   {
    //     frontmatter,
    //     route,
    //   },
    //   true
    // )
  },
}

export default theme
