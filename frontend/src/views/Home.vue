<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { problemsApi } from '../api/problems'
import { rankingApi } from '../api/ranking'

const router = useRouter()
const auth = useAuthStore()

const recentProblems = ref([])
const topUsers = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [pRes, rRes] = await Promise.all([
      problemsApi.getList({ size: 5, sort_by: 'created_at', sort_order: 'desc' }),
      rankingApi.getList({ size: 5 }),
    ])
    if (pRes.code === 0) recentProblems.value = pRes.data.list || []
    if (rRes.code === 0) topUsers.value = rRes.data.list || []
  } catch { /* ignore */ }
  loading.value = false
})

function statusClass(status) {
  return `status-${(status || '').replace(/_/g, '-')}`
}
</script>

<template>
  <div class="home">
    <div v-if="!auth.isLoggedIn" class="hero card text-center">
      <h1>欢迎来到 QuickOJ</h1>
      <p class="text-muted mt-1">快速、简洁的算法竞赛在线评测平台 —— 刷题、提交、排行榜</p>
      <div class="mt-2">
        <router-link to="/register" class="btn btn-primary btn-lg mr-1">立即注册</router-link>
        <router-link to="/problems" class="btn btn-outline btn-lg">浏览题库</router-link>
      </div>
    </div>

    <div v-if="auth.isLoggedIn" class="hero card">
      <h1>欢迎回来，{{ auth.user?.username }}</h1>
      <p class="text-muted mt-1">
        已通过 <strong>{{ auth.user?.solved_problems || 0 }}</strong> 题，
        共提交 <strong>{{ auth.user?.total_submissions || 0 }}</strong> 次
      </p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="home-grid">
      <div class="card">
        <div class="flex-between mb-2">
          <h2 class="card-title" style="margin-bottom:0">最新题目</h2>
          <router-link to="/problems" class="text-sm">查看全部 →</router-link>
        </div>
        <div v-if="recentProblems.length === 0" class="text-muted text-sm">暂无题目</div>
        <div v-else class="problem-list-simple">
          <router-link
            v-for="p in recentProblems" :key="p.problem_id"
            :to="`/problems/${p.problem_number || 'p' + p.problem_id}`"
            class="problem-item"
          >
            <span class="problem-number">{{ p.problem_number || '#' + p.problem_id }}</span>
            <span class="problem-name">{{ p.problem_name }}</span>
            <span class="problem-meta text-muted">{{ p.problem_type }} · 难度 {{ p.difficulty }}</span>
          </router-link>
        </div>
      </div>

      <div class="card">
        <div class="flex-between mb-2">
          <h2 class="card-title" style="margin-bottom:0">排行榜 TOP5</h2>
          <router-link to="/ranking" class="text-sm">查看全部 →</router-link>
        </div>
        <div v-if="topUsers.length === 0" class="text-muted text-sm">暂无数据</div>
        <div v-else class="rank-list-simple">
          <div v-for="u in topUsers" :key="u.user_id" class="rank-item">
            <span class="rank-num">{{ u.rank }}</span>
            <router-link :to="`/user/${u.user_id}`">{{ u.username }}</router-link>
            <span class="text-muted text-sm">{{ u.solved_problems }} 题</span>
          </div>
        </div>
      </div>
    </div>

    <div class="text-center mt-3">
      <router-link to="/problems" class="btn btn-primary btn-lg">进入题库</router-link>
    </div>
  </div>
</template>

<style scoped>
.hero { padding: 40px; }
.hero h1 { font-size: 28px; }
.home-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}
@media (max-width: 768px) { .home-grid { grid-template-columns: 1fr; } }

.problem-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--gray-100);
  color: inherit;
}
.problem-item:hover { color: var(--primary); }
.problem-number { font-weight: 600; min-width: 60px; color: var(--primary); }

.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--gray-100);
}
.rank-num {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}
</style>
