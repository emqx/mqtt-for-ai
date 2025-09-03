<template>
  <div class="specs-section">
    <div class="container">
      <SpecCard title="Model Context Protocol (MCP) over MQTT"
        intro="Extends MQTT 5.0 with AI model management capabilities:" :features="[
          'Dynamic model deployment and versioning',
          'Model state synchronization across devices',
          'Efficient model parameter distribution',
          'Real-time model performance monitoring'
        ]" link="/mcp-over-mqtt/"
        caption="MCP enables seamless model distribution and synchronization across devices">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <rect x="50" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="100" y="100" text-anchor="middle" class="diagram-text">AI Model</text>
            <path d="M150 100 L250 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <rect x="250" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="300" y="100" text-anchor="middle" class="diagram-text">MQTT Broker</text>
            <path d="M350 100 L450 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <rect x="450" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="500" y="100" text-anchor="middle" class="diagram-text">Edge Device</text>
          </svg>
        </template>
      </SpecCard>

      <SpecCard title="MQTT/RT" intro="Real-time messaging bus for robotics and automation:"
        :features="[
          'Deterministic message delivery guarantees',
          'Ultra-low latency communication',
          'Priority-based message scheduling',
          'Time-synchronized device coordination'
        ]" link="/mqtt-rt/" caption="Deterministic communication between robotics components">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <circle cx="150" cy="100" r="40" fill="currentColor" class="diagram-shape" />
            <text x="150" y="100" text-anchor="middle" class="diagram-text">Robot</text>
            <circle cx="300" cy="100" r="40" fill="currentColor" class="diagram-shape" />
            <text x="300" y="100" text-anchor="middle" class="diagram-text">Controller</text>
            <circle cx="450" cy="100" r="40" fill="currentColor" class="diagram-shape" />
            <text x="450" y="100" text-anchor="middle" class="diagram-text">Sensor</text>
            <path d="M150 100 L300 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <path d="M300 100 L450 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
          </svg>
        </template>
      </SpecCard>

      <SpecCard title="MQTT over QUIC"
        intro="Modern transport layer implementation for enhanced performance:" :features="[
          'Improved connection establishment and migration',
          'Better congestion control and loss recovery',
          'Enhanced security with built-in TLS 1.3',
          'Stream multiplexing for efficient data transfer'
        ]" link="/mqtt-quic/" caption="QUIC provides multiple streams over a single connection">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <rect x="50" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="100" y="100" text-anchor="middle" class="diagram-text">Client</text>
            <path d="M150 100 Q300 50 450 100" stroke="currentColor" stroke-width="2" fill="none"
              class="diagram-curve" />
            <path d="M150 100 Q300 150 450 100" stroke="currentColor" stroke-width="2" fill="none"
              class="diagram-curve" />
            <rect x="450" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="500" y="100" text-anchor="middle" class="diagram-text">Server</text>
          </svg>
        </template>
      </SpecCard>

      <SpecCard title="MQTT Queues and Streams"
        intro="MQTT with powerful queueing and streaming capabilities:" :features="[
          'Reliable message queues with FIFO delivery',
          'High-throughput data streams with replay support',
          'Flexible configuration options',
          'Fully compatible with MQTT 5.0 clients'
        ]" link="/mqtt-queues-streams/"
        caption="Enterprise messaging patterns in your MQTT ecosystem">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <!-- Producer side -->
            <rect x="50" y="50" width="100" height="40" fill="currentColor" class="diagram-shape" />
            <text x="100" y="75" text-anchor="middle" class="diagram-text">Producer</text>

            <!-- Flow from producer -->
            <path d="M150 70 L200 70" stroke="currentColor" stroke-width="2" class="diagram-line" />

            <!-- Broker with queues and streams -->
            <rect x="200" y="40" width="200" height="120" fill="currentColor"
              class="diagram-shape" />
            <text x="300" y="65" text-anchor="middle" class="diagram-text">MQTT Broker</text>

            <!-- Queue representation -->
            <rect x="220" y="80" width="160" height="25" fill="none" stroke="currentColor"
              stroke-width="1" />
            <text x="245" y="97" text-anchor="middle" class="diagram-text">$queue/</text>
            <rect x="220" y="115" width="160" height="25" fill="none" stroke="currentColor"
              stroke-width="1" />
            <text x="245" y="132" text-anchor="middle" class="diagram-text">$stream/</text>

            <!-- Messages in queue -->
            <rect x="280" y="85" width="15" height="15" fill="currentColor" />
            <rect x="305" y="85" width="15" height="15" fill="currentColor" />
            <rect x="330" y="85" width="15" height="15" fill="currentColor" />
            <rect x="355" y="85" width="15" height="15" fill="currentColor" />

            <!-- Messages in stream -->
            <rect x="280" y="120" width="15" height="15" fill="currentColor" />
            <rect x="305" y="120" width="15" height="15" fill="currentColor" />
            <rect x="330" y="120" width="15" height="15" fill="currentColor" />
            <rect x="355" y="120" width="15" height="15" fill="currentColor" />

            <!-- Flow to consumers -->
            <path d="M400 90 L450 70" stroke="currentColor" stroke-width="2" class="diagram-line" />
            <path d="M400 120 L450 130" stroke="currentColor" stroke-width="2"
              class="diagram-line" />

            <!-- Consumers -->
            <rect x="450" y="50" width="100" height="40" fill="currentColor"
              class="diagram-shape" />
            <text x="500" y="75" text-anchor="middle" class="diagram-text">Queue Consumer</text>
            <rect x="450" y="110" width="100" height="40" fill="currentColor"
              class="diagram-shape" />
            <text x="500" y="135" text-anchor="middle" class="diagram-text">Stream Consumer</text>
          </svg>
        </template>
      </SpecCard>

      <SpecCard title="MQTT Subscription Filters"
        intro="Enhanced topic filtering capabilities for efficient message routing:" :features="[
          'Advanced pattern matching with regular expressions',
          'Logical operators for complex filter conditions',
          'Time-based and state-based filtering',
          'Optimized performance with pattern compilation'
        ]" link="/mqtt-subscription-filters/"
        caption="Advanced filtering enables precise message routing and processing">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <rect x="50" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="100" y="100" text-anchor="middle" class="diagram-text">Client</text>
            <path d="M150 100 L250 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <rect x="250" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="300" y="100" text-anchor="middle" class="diagram-text">Filter</text>
            <path d="M350 100 L450 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <rect x="450" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="500" y="100" text-anchor="middle" class="diagram-text">Topic</text>
          </svg>
        </template>
      </SpecCard>

      <SpecCard title="MQTT Batch Publishing"
        intro="Optimized message batching for high-throughput scenarios:" :features="[
          'Multiple logical messages in a single MQTT packet',
          'Reduced network overhead and improved efficiency',
          'Compatible with standard MQTT 5.0 clients',
          'Configurable batch size and payload limits'
        ]" link="/mqtt-batch-publishing/"
        caption="Efficiently batch multiple messages for improved throughput">
        <template #diagram>
          <svg viewBox="0 0 600 200" class="diagram">
            <!-- Publisher side -->
            <rect x="50" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="100" y="100" text-anchor="middle" class="diagram-text">Publisher</text>

            <!-- Small messages being batched -->
            <rect x="175" y="60" width="20" height="20" fill="currentColor" class="diagram-shape" />
            <rect x="175" y="90" width="20" height="20" fill="currentColor" class="diagram-shape" />
            <rect x="175" y="120" width="20" height="20" fill="currentColor"
              class="diagram-shape" />

            <!-- Arrows from publisher to messages -->
            <path d="M150 80 L175 70" stroke="currentColor" stroke-width="2" class="diagram-line" />
            <path d="M150 100 L175 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <path d="M150 120 L175 130" stroke="currentColor" stroke-width="2"
              class="diagram-line" />

            <!-- Batch container -->
            <rect x="220" y="50" width="60" height="100" fill="none" stroke="currentColor"
              stroke-width="2" />
            <text x="250" y="40" text-anchor="middle" class="diagram-text">Batch</text>

            <!-- Arrows from messages to batch -->
            <path d="M195 70 L220 70" stroke="currentColor" stroke-width="2" class="diagram-line" />
            <path d="M195 100 L220 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />
            <path d="M195 130 L220 130" stroke="currentColor" stroke-width="2"
              class="diagram-line" />

            <!-- Arrow from batch to broker -->
            <path d="M280 100 L350 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />

            <!-- Broker -->
            <rect x="350" y="50" width="100" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="400" y="100" text-anchor="middle" class="diagram-text">MQTT Broker</text>

            <!-- Arrow from broker to subscribers -->
            <path d="M450 100 L520 100" stroke="currentColor" stroke-width="2"
              class="diagram-line" />

            <!-- Subscriber -->
            <rect x="520" y="50" width="40" height="100" fill="currentColor"
              class="diagram-shape" />
            <text x="540" y="100" text-anchor="middle" class="diagram-text">Sub</text>
          </svg>
        </template>
      </SpecCard>
    </div>
  </div>
</template>

<script setup>
import SpecCard from './SpecCard.vue'
</script>

<style scoped>
.specs-section {
  padding: 2rem 0 4rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.diagram {
  width: 100%;
  height: auto;
}

.diagram-shape {
  opacity: 0.1;
}

.diagram-text {
  fill: var(--vp-c-text-1);
  font-size: 14px;
}

.diagram-line,
.diagram-curve {
  stroke: var(--vp-c-indigo-1);
}

:deep(.dark) .diagram-text {
  fill: var(--vp-c-text-1);
}

:deep(.dark) .diagram-shape {
  fill: var(--vp-c-indigo-1);
}
</style>