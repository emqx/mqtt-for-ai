export interface RepoConfig {
  /** GitHub repository path */
  repo: string
  /** Documentation target directory */
  target: string
  /** Documentation source directory */
  source: string
  /** Git branch */
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
