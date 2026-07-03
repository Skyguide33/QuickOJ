<script setup>
import { ref, onMounted } from 'vue'
import { assetUrl } from '../utils/time'
import { rankingApi } from '../api/ranking'
defineOptions({ name: 'Ranking' })
import Pagination from '../components/Pagination.vue'

const users = ref([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const size = 20

async function fetchData() {
  loading.value = true
  try {
    const res = await rankingApi.getList({ page: page.value, size })
    if (res.code === 0) {
      users.value = res.data.list
      total.value = res.data.pagination.total
    }
  } catch { /* ignore */ }
  loading.value = false
}

function onPageChange(p) { page.value = p; fetchData() }

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="page-header"><h1>排行榜</h1></div>
    <p class="text-muted mb-2">排名按解题数降序，解题数相同时按总提交数升序（提交少者优先）</p>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="card table-container" style="padding:0">
      <table>
        <thead>
          <tr>
            <th style="width:60px">排名</th>
            <th>用户</th>
            <th style="width:120px">解题数</th>
            <th style="width:120px">总提交</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.user_id">
            <td>
              <span class="rank-num" :class="{ 'top3': u.rank <= 3 }">{{ u.rank }}</span>
            </td>
            <td>
              <router-link :to="`/user/${u.user_id}`" class="flex gap-1" style="align-items:center">
                <img v-if="u.avatar" :src="assetUrl(u.avatar)" class="avatar-sm" />
                <span>{{ u.username }}</span>
              </router-link>
            </td>
            <td><strong>{{ u.solved_problems }}</strong></td>
            <td class="text-muted">{{ u.total_submissions }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination :page="page" :size="size" :total="total" @change="onPageChange" />
  </div>
</template>

<style scoped>
.rank-num {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 14px;
}
.rank-num.top3 { background: var(--primary-light); color: var(--primary); }
.avatar-sm {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
}
</style>
