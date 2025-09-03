<template>
  <div class="community-section">
    <h2 class="community-title">Join Our Community</h2>
    <div class="community-grid">
      <div v-for="item in communityItems" :key="item.title" class="community-card">
        <h3 class="community-card-title">{{ item.title }}</h3>
        <p class="community-card-description">{{ item.description }}</p>
        <a :href="item.link" target="_blank" class="community-link"></a>
      </div>
    </div>
  </div>
</template>

<script setup>
const communityItems = [
  {
    title: 'GitHub',
    description: 'Contribute to our open-source projects, report issues, and collaborate with developers worldwide.',
    link: 'https://github.com/mqtt-ai',
    linkText: 'View on GitHub →'
  },
  {
    title: 'Discord',
    description: 'Join our Discord server to chat with the community, get help, and share your experiences.',
    link: '#',
    linkText: 'Join Discord →'
  },
  {
    title: 'Blog',
    description: 'Read the latest updates, tutorials, and insights about MQTT.AI and its applications.',
    link: '#',
    linkText: 'Read Blog →'
  },
  {
    title: 'Events',
    description: 'Participate in our webinars, meetups, and conferences to learn and network with experts.',
    link: '#',
    linkText: 'View Events →'
  }
]
</script>

<style scoped>
.community-section {
  padding: 4rem 0;
  background-color: var(--vp-c-bg);
}

.community-title {
  text-align: center;
  margin-bottom: 3rem;
  color: var(--vp-c-text-1);
  font-weight: 700;
  font-size: 2rem;
}

.community-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.community-card {
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

.community-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--vp-shadow-3);
}

.community-card-title {
  color: var(--vp-c-indigo-1);
  margin-bottom: 1rem;
  font-weight: 600;
}

.community-card-description {
  margin-bottom: 1.5rem;
  color: var(--vp-c-text-2);
  flex-grow: 1;
}

.community-link {
  display: inline-block;
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}

.community-link::after {
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

.community-card:hover .community-link::after {
  transform: translateX(10px);
}

@media (max-width: 768px) {
  .community-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
}
</style>