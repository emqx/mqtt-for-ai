<template>
  <div class="powered-by-section">
    <div class="powered-by-content">
      <div class="powered-by-text">
        <h2 class="powered-by-title">Powered by EMQ</h2>
        <p class="powered-by-description">EMQ pioneers the world's first MQTT and AI platform,
          transforming IoT data streams from manufacturing, autonomous driving, and robotics into
          real-time intelligence.</p>
        <a href="https://www.emqx.com/en" class="powered-by-link" target="_blank">Learn more about
          EMQ
          →</a>
      </div>
      <div class="powered-by-logo">
        <img src="/emq.svg" alt="EMQ Logo" width="120" class="logo-img">
      </div>
    </div>
  </div>
</template>

<style scoped>
.powered-by-section {
  padding: 4rem 0;
  margin-bottom: 4rem;
  background-color: var(--vp-c-bg-soft);
  border-radius: 0.5rem;
}

.powered-by {
  padding: 4rem 0;
  background-color: var(--vp-c-bg-soft);
}

.powered-by-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4rem;
  max-width: 800px;
  margin: 0 auto;
}

.powered-by-text {
  flex: 1;
}

.powered-by-title {
  color: var(--vp-c-indigo-1);
  margin-bottom: 1rem;
  font-weight: 600;
}

.powered-by-description {
  margin-bottom: 1.5rem;
  color: var(--vp-c-text-2);
}

.powered-by-link {
  color: var(--vp-c-indigo-1);
  text-decoration: none;
  font-weight: bold;
  transition: color 0.3s;
}

.powered-by-link:hover {
  color: var(--vp-c-indigo-2);
  text-decoration: underline;
}

.powered-by-logo {
  flex-shrink: 0;
}

.logo-img {
  filter: var(--image-filter);
}

@media (max-width: 768px) {
  .powered-by-content {
    flex-direction: column;
    text-align: center;
    gap: 2rem;
  }
}

:root {
  --image-filter: none;
}

.dark {
  --image-filter: brightness(0) invert(1);
}
</style>