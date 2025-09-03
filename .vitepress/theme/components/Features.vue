<template>
  <div class="features-section">
    <div class="features-grid">
      <div v-for="feature in features" :key="feature.title" class="feature-card">
        <h3 class="feature-title">{{ feature.title }}</h3>
        <p class="feature-description">{{ feature.description }}</p>
        <a :href="withBase(feature.link)" class="feature-link"></a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { withBase } from 'vitepress'

const features = [
  {
    title: 'MCP over MQTT',
    description: 'Model Context Protocol for AI model management and coordination over MQTT, enabling efficient model deployment and inference.',
    link: '/mcp-over-mqtt/'
  },
  {
    title: 'MQTT/RT',
    description: 'Realtime messaging bus for robotics and automation, providing deterministic, low-latency communication.',
    link: '/mqtt-rt/'
  },
  {
    title: 'MQTT over QUIC',
    description: 'Modern transport protocol implementation for improved performance, security, and reliability in IoT communications.',
    link: '/mqtt-quic/'
  },
  {
    title: 'MQTT Queues and Streams',
    description: 'Add enterprise messaging patterns to MQTT 5.0 with persistent queues and high-throughput streams while maintaining protocol compatibility.',
    link: '/mqtt-queues-streams/'
  },
  {
    title: 'MQTT Subscription Filters',
    description: 'Enhanced topic filtering capabilities with advanced pattern matching, logical operators, and optimized performance.',
    link: '/mqtt-subscription-filters/'
  },
  {
    title: 'MQTT Batch Publishing',
    description: 'Optimize message delivery by sending multiple logical messages within a single MQTT packet, reducing overhead and improving throughput.',
    link: '/mqtt-batch-publishing/'
  }
]
</script>

<style scoped>
.features-section {
  padding: 4rem 0;
}

.features {
  padding: 4rem 0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
  width: 100%;
}

.feature-card {
  background-color: var(--vp-c-bg-soft);
  padding: 2rem;
  border-radius: 0.5rem;
  box-shadow: var(--vp-shadow-2);
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--vp-shadow-3);
}

.feature-title {
  color: var(--vp-c-indigo-1);
  margin-bottom: 1rem;
  font-size: 1.5rem;
  line-height: 1.3;
  font-weight: 600;
}

.feature-description {
  margin-bottom: 1.5rem;
  line-height: 1.6;
  flex-grow: 1;
}

.feature-link {
  display: inline-block;
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}

.feature-link::after {
  content: "→";
  display: block;
  position: absolute;
  right: 2rem;
  bottom: 2rem;
  color: var(--vp-c-indigo-1);
  font-size: 1.5rem;
  font-weight: normal;
  transition: transform 0.3s ease;
}

.feature-card:hover .feature-link::after {
  transform: translateX(10px);
}

@media (max-width: 768px) {
  .features-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}
</style>