<script setup>
import Navbar from './components/Navbar.vue'
</script>

<template>
  <div id="quickoj-app">
    <Navbar />
    <main class="main-container">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['ProblemList', 'SubmissionList', 'Ranking']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.main-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
  min-height: calc(100vh - 60px);
}
</style>
