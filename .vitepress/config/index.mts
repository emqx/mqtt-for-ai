import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'
// 加载动态侧边栏配置
function loadSidebarConfigs() {
  const docsDir = path.resolve(__dirname, '../../docs')
  const sidebar: Record<string, any> = {}

  try {
    // 获取所有子目录
    const dirs = fs
      .readdirSync(docsDir, { withFileTypes: true })
      .filter((dirent) => dirent.isDirectory())
      .map((dirent) => dirent.name)

    // 处理每个子目录中的 sidebar.json
    for (const dir of dirs) {
      const sidebarPath = path.join(docsDir, dir, 'sidebar.json')

      try {
        if (fs.existsSync(sidebarPath)) {
          const sidebarContent = fs.readFileSync(sidebarPath, 'utf-8')
          const sidebarConfig = JSON.parse(sidebarContent)

          // 如果 sidebar.json 有有效的配置，添加到总配置中
          if (sidebarConfig.path && sidebarConfig.items) {
            sidebar[sidebarConfig.path] = sidebarConfig.items
          }
        }
      } catch (err) {
        console.error(`加载侧边栏配置失败: ${sidebarPath}`, err)
      }
    }
  } catch (err) {
    console.error('加载侧边栏配置出错:', err)
  }

  return sidebar
}

// Check if test environment
const isTestEnv = process.env.TEST_ENV === 'true'

// https://vitepress.dev/reference/site-config
export default withMermaid({
  ...defineConfig({
    title: 'MQTT.AI',
    description: 'MQTT.AI - Next-Generation MQTT Protocol for AI',

    vite: {
      plugins: [tailwindcss()],
    },

    sitemap: {
      hostname: 'https://mqtt.ai',
    },

    buildEnd: ({ outDir }) => {
      // Generate robots.txt only in test environment
      if (isTestEnv) {
        const testRobotsContent = 'User-agent: *\nDisallow: /\n'
        fs.writeFileSync(path.resolve(outDir, 'robots.txt'), testRobotsContent)
        console.log('✓ Generated robots.txt for test environment (disallow indexing)')
      } else {
        console.log('✓ Using production robots.txt (allow indexing)')
      }
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

      // editLink: {
      //   pattern: 'https://github.com/emqx/mcp-over-mqtt-site/edit/main/:path',
      // },

      nav: [{ text: 'Contact Us', link: 'mailto:mqtt@emqx.io' }],

      // 从各个项目目录加载动态侧边栏配置
      sidebar: loadSidebarConfigs(),

      socialLinks: [
        { icon: 'github', link: 'https://github.com/mqtt-ai' },
        { icon: 'slack', link: 'https://emqx.slack.com/' },
      ],
    },
  }),
})
