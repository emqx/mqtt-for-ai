export interface RepoConfig {
  /** GitHub 仓库路径 */
  repo: string
  /** 文档目标目录 */
  target: string
  /** 文档源目录 */
  source: string
  /** Git 分支 */
  branch: string
}

export const repos: RepoConfig[] = [
  {
    repo: 'mqtt-ai/mcp-over-mqtt',
    target: 'mcp-over-mqtt',
    source: '',
    branch: 'main',
  },
  {
    repo: 'mqtt-ai/mqtt-over-quic',
    target: 'mqtt-quic',
    source: '',
    branch: 'main',
  },
  {
    repo: 'mqtt-ai/mqtt-rt',
    target: 'mqtt-rt',
    source: '',
    branch: 'main',
  },
  {
    repo: 'mqtt-ai/mqtt-queues-streams',
    target: 'mqtt-queues-streams',
    source: '',
    branch: 'main',
  },
  {
    repo: 'mqtt-ai/mqtt-subscription-filters',
    target: 'mqtt-subscription-filters',
    source: '',
    branch: 'main',
  },
  {
    repo: 'mqtt-ai/mqtt-batch-publishing',
    target: 'mqtt-batch-publishing',
    source: '',
    branch: 'main',
  },
]

export default repos
