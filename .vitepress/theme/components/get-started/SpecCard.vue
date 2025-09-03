<template>
  <div class="spec-card">
    <div class="spec-content">
      <h2>{{ title }}</h2>
      <p>{{ intro }}</p>
      <ul>
        <li v-for="(item, index) in features" :key="index">{{ item }}</li>
      </ul>
      <a :href="withBase(link)" class="spec-link">View Full Specification →</a>
    </div>
    <div class="spec-diagram">
      <slot name="diagram"></slot>
      <div class="diagram-caption">{{ caption }}</div>
    </div>
  </div>
</template>

<script setup>
import { withBase } from 'vitepress'

defineProps({
  title: {
    type: String,
    required: true
  },
  intro: {
    type: String,
    required: true
  },
  features: {
    type: Array,
    required: true
  },
  link: {
    type: String,
    required: true
  },
  caption: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
.spec-card {
  background: var(--vp-c-bg-soft);
  padding: 2rem;
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  margin-bottom: 2.5rem;
  display: flex;
  gap: 2rem;
  align-items: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  overflow: hidden;
}

.spec-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
}

.spec-content {
  flex: 1.2;
}

.spec-card h2 {
  color: var(--vp-c-indigo-1);
  margin-bottom: 1.5rem;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.3;
  position: relative;
  padding-bottom: 0.75rem;
}

.spec-card h2::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 3rem;
  height: 3px;
  background: var(--vp-c-indigo-1);
  border-radius: 2px;
}

.spec-card p {
  margin-bottom: 1rem;
  color: var(--vp-c-text-2);
}

.spec-card ul {
  padding-left: 1.5rem;
  margin-bottom: 1.5rem;
}

.spec-card li {
  margin-bottom: 0.5rem;
  color: var(--vp-c-text-2);
  position: relative;
}

.spec-card li::before {
  content: "•";
  color: var(--vp-c-indigo-1);
  font-weight: bold;
  position: absolute;
  left: -1rem;
}

.spec-link {
  display: inline-block;
  color: var(--vp-c-indigo-1);
  text-decoration: none;
  margin-top: 1rem;
  font-weight: bold;
  position: relative;
  padding: 0.5rem 0;
}

.spec-link::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--vp-c-indigo-1);
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.3s ease;
}

.spec-link:hover::after {
  transform: scaleX(1);
  transform-origin: left;
}

.spec-diagram {
  flex: 1;
  position: relative;
  background: linear-gradient(135deg, var(--vp-c-bg-alt) 0%, var(--vp-c-bg) 100%);
  border-radius: 1rem;
  padding: 1.5rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.spec-diagram::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.diagram-caption {
  text-align: center;
  color: var(--vp-c-text-3);
  font-size: 0.9rem;
  margin-top: 1rem;
  font-style: italic;
}

:deep(.diagram) {
  width: 100%;
  height: auto;
  max-width: 400px;
}

:deep(.diagram-shape) {
  opacity: 0.2;
  fill: var(--vp-c-indigo-1);
}

:deep(.diagram-text) {
  fill: var(--vp-c-text-1);
  font-size: 14px;
  font-weight: 500;
}

:deep(.diagram-line),
:deep(.diagram-curve) {
  stroke: var(--vp-c-indigo-1);
  stroke-dasharray: 5;
  animation: dashFlow 20s linear infinite;
}

@keyframes dashFlow {
  to {
    stroke-dashoffset: -1000;
  }
}

@media (max-width: 768px) {
  .spec-card {
    flex-direction: column;
  }

  .spec-diagram {
    width: 100%;
    padding: 1.5rem 1rem;
  }
}
</style>