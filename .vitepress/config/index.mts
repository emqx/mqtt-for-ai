import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'
// Load dynamic sidebar configurations
function loadSidebarConfigs() {
  const docsDir = path.resolve(__dirname, '../../')
  const sidebar: Record<string, any> = {}

  try {
    // Get all subdirectories
    const dirs = fs
      .readdirSync(docsDir, { withFileTypes: true })
      .filter((dirent) => dirent.isDirectory())
      .map((dirent) => dirent.name)

    // Process sidebar.json in each subdirectory
    for (const dir of dirs) {
      const sidebarPath = path.join(docsDir, dir, 'sidebar.json')

      try {
        if (fs.existsSync(sidebarPath)) {
          const sidebarContent = fs.readFileSync(sidebarPath, 'utf-8')
          const sidebarConfig = JSON.parse(sidebarContent)

          // If sidebar.json has valid configuration, add to main config
          if (sidebarConfig.path && sidebarConfig.items) {
            sidebar[sidebarConfig.path] = sidebarConfig.items
          }
        }
      } catch (err) {
        console.error(`Failed to load sidebar config: ${sidebarPath}`, err)
      }
    }
  } catch (err) {
    console.error('Error loading sidebar configs:', err)
  }

  return sidebar
}

// https://vitepress.dev/reference/site-config
export default withMermaid({
  ...defineConfig({
    base: '/mqtt-for-ai/',

    title: 'MQTT.AI',
    description: 'MQTT.AI - Next-Generation MQTT Protocol for AI',

    vite: {
      plugins: [tailwindcss()],
    },

    sitemap: {
      hostname: 'https://www.emqx.com/mqtt-for-ai/',
    },

    srcExclude: ['**/README.md', 'temp/**'],

    themeConfig: {
      // https://vitepress.dev/reference/default-theme-config

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

      // Load dynamic sidebar configurations from each project directory
      sidebar: loadSidebarConfigs(),

      socialLinks: [
        { icon: 'github', link: 'https://github.com/emqx/mqtt-for-ai' },
        { icon: 'slack', link: 'https://emqx.slack.com/' },
      ],
    },
  }),
})
