<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'
import VPImage from 'vitepress/dist/client/theme-default/components/VPImage.vue'

const { site, theme } = useData()

const link = computed(() =>
  typeof theme.value.logoLink === 'string'
    ? theme.value.logoLink
    : (theme.value.logoLink as { link?: string })?.link
)

const isExternal = computed(() => link.value?.startsWith('http'))
</script>

<template>
  <div class="VPNavBarTitle" :class="{ 'vp-raw': isExternal }">
    <a
      class="title"
      :href="link ?? '/'"
    >
      <VPImage v-if="theme.logo" class="logo" :image="theme.logo" />
      <span v-if="theme.siteTitle">{{ theme.siteTitle }}</span>
      <span v-else-if="theme.siteTitle === undefined">{{ site.title }}</span>
    </a>
  </div>
</template>

<style scoped>
.title {
  display: flex;
  align-items: center;
  border-bottom: 1px solid transparent;
  width: 100%;
  height: var(--vp-nav-height);
  font-size: 16px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  transition: opacity 0.25s;
}

@media (min-width: 960px) {
  .title {
    flex-shrink: 0;
  }

  .VPNavBarTitle.has-sidebar .title {
    border-bottom-color: var(--vp-c-divider);
  }
}

:deep(.logo) {
  margin-right: 8px;
  height: var(--vp-nav-logo-height);
}
</style>
