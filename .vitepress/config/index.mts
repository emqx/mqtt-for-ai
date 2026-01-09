import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import tailwindcss from '@tailwindcss/vite'
import { sidebar } from './sidebar.mts'

// https://vitepress.dev/reference/site-config
export default withMermaid({
  ...defineConfig({
    base: '/mqtt-for-ai/',

    title: 'MQTT.AI',
    description: 'MQTT.AI - Next-Generation MQTT Protocol for AI',

    head: [['link', { rel: 'icon', href: '/mqtt-for-ai/favicon.ico' }]],

    vite: {
      plugins: [tailwindcss()],
    },

    sitemap: {
      hostname: 'https://www.emqx.com/mqtt-for-ai/',
    },

    srcExclude: ['**/README.md', 'temp/**'],

    themeConfig: {
      // https://vitepress.dev/reference/default-theme-config

      logoLink: {
        link: 'https://www.emqx.com/en/mqtt-for-ai',
        rel: 'external',
      },

      notFound: {
        linkText: 'Go to Homepage',
        link: 'https://www.emqx.com/en/mqtt-for-ai',
      } as { linkText: string; link: string },

      footer: {
        copyright: '© 2025 MQTT.AI. All rights reserved.',
      },

      search: {
        provider: 'local',
      },

      editLink: {
        pattern: 'https://github.com/emqx/mqtt-for-ai/edit/main/:path',
      },

      nav: [{ text: 'Contact Us', link: 'mailto:mqtt@emqx.io' }],

      sidebar,

      socialLinks: [
        { icon: 'github', link: 'https://github.com/emqx/mqtt-for-ai' },
        { icon: 'slack', link: 'https://emqx.slack.com/' },
      ],
    },
  }),
})
