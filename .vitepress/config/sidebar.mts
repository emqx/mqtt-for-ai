import type { DefaultTheme } from 'vitepress'

export const sidebar: DefaultTheme.Config['sidebar'] = [
  {
    text: 'MCP over MQTT',
    collapsed: true,
    items: [
      {
        text: 'Overview',
        link: '/mcp-over-mqtt/',
      },
      {
        text: 'Use Cases',
        link: '/mcp-over-mqtt/use-cases',
      },
      {
        text: 'Architecture',
        link: '/mcp-over-mqtt/specification/2025-03-26/basic/architecture',
      },
      {
        text: 'MQTT Transport',
        link: '/mcp-over-mqtt/specification/2025-03-26/basic/mqtt_transport',
      },
      {
        text: 'SDKs',
        collapsed: true,
        items: [
          {
            text: 'Python SDK',
            link: '/mcp-over-mqtt/sdk/python/',
          },
        ],
      },
    ],
  },
  {
    text: 'MQTT-RT',
    link: '/mqtt-rt/',
  },
  {
    text: 'MQTT over QUIC',
    link: '/mqtt-quic/',
  },
  {
    text: 'MQTT Queues & Streams',
    link: '/mqtt-queues-streams/',
  },
  {
    text: 'MQTT Subscription Filters',
    link: '/mqtt-subscription-filters/',
  },
  {
    text: 'MQTT Batch Publishing',
    link: '/mqtt-batch-publishing/',
  },
]
