<script setup lang="ts">
import { withBase } from 'vitepress'
</script>

<template>
  <div class="hero-section">
    <h1 class="hero-title">MQTT for AI</h1>
    <p class="hero-description">Enhancing MQTT 5.0 with AI capabilities, real-time messaging bus,
      queuing and data streaming, and modern transport protocols. Accelerating the future of agentic
      and physical AI.</p>
    <div class="hero-buttons">
      <a :href="withBase('/get-started.html')" class="hero-button primary">Get Started</a>
      <a href="mailto:mqtt@emqx.io" class="hero-button secondary">Contact Us</a>
    </div>
  </div>
</template>

<style scoped>
.hero-section {
  padding: 4rem 0;
  text-align: center;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: bold;
  line-height: 1.2;
  margin-bottom: 1.5rem;
}

.hero-description {
  font-size: 1.25rem;
  max-width: 700px;
  margin: 0 auto 2rem;
  line-height: 1.6;
  opacity: 0.9;
}

.hero-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 2rem;
}

.hero-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.3s ease;
}

.hero-button.primary {
  background: var(--vp-c-indigo-1);
  color: white;
}

.hero-button.primary:hover {
  background: var(--vp-c-indigo-2);
  transform: translateY(-2px);
}

.hero-button.secondary {
  border: 1px solid var(--vp-c-indigo-1);
  color: var(--vp-c-indigo-1);
}

.hero-button.secondary:hover {
  background: var(--vp-c-indigo-soft);
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .hero-buttons {
    flex-direction: column;
    align-items: center;
  }

  .hero-button {
    width: 100%;
    max-width: 300px;
    text-align: center;
  }
}
</style>