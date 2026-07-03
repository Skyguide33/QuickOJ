<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
defineOptions({ name: 'ProblemList' })
import { useAuthStore } from '../stores/auth'
import { problemsApi } from '../api/problems'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const problems = ref([])
const total = ref(0)
const reviewCount = ref(0)
const pendingNewCount = ref(0)
const pendingModifyCount = ref(0)
const loading = ref(true)

const page = ref(1)
const size = 20
const keyword = ref('')
const difficultyMin = ref(null)
const difficultyMax = ref(null)
const problemType = ref('')
const status = ref('')
const reviewMode = ref(false)
const hideSolved = ref(false)
const sortBy = ref('problem_number')
const sortOrder = ref('asc')

const presets = [
  { label: '800-', min: null, max: 800 },
  { label: '800~1200', min: 800, max: 1200 },
  { label: '1200~1600', min: 1200, max: 1600 },
  { label: '1600~2000', min: 1600, max: 2000 },
  { label: '2000+', min: 2000, max: null },
]

async function fetchProblems() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      size,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    }
    if (keyword.value) params.keyword = keyword.value
    if (difficultyMin.value) params.difficulty_min = difficultyMin.value
    if (difficultyMax.value) params.difficulty_max = difficultyMax.value
    if (problemType.value) params.problem_type = problemType.value
    // status 优先于 review_mode：选定具体状态后不再发 review_mode
    if (status.value) {
      params.status = status.value
    } else if (reviewMode.value) {
      params.review_mode = true
    }
    if (hideSolved.value) params.hide_solved = true

    const res = await problemsApi.getList(params)
    if (res.code === 0) {
      problems.value = res.data.list
      total.value = res.data.pagination.total
      reviewCount.value = res.data.review_count || 0
      pendingNewCount.value = res.data.pending_new_count || 0
      pendingModifyCount.value = res.data.pending_modify_count || 0
      // 从「题目审核」进入 → 自动选择最优先的待审核状态（仅首次）
      if (reviewMode.value && !status.value) {
        if (res.data.pending_new_count > 0) {
          status.value = 'pending_new'
          reviewMode.value = false
          return fetchProblems()
        } else if (res.data.pending_modify_count > 0) {
          status.value = 'pending_modify'
          reviewMode.value = false
          return fetchProblems()
        } else {
          // 无待审核题目 → 清除筛选，跳转到普通题库页
          reviewMode.value = false
          router.replace({ query: {} })
          return fetchProblems()
        }
      }
    }
  } catch { /* ignore */ }
  loading.value = false
}

function applyPreset(p) {
  // 已选中同一预设 → 取消筛选
  if (difficultyMin.value === p.min && difficultyMax.value === p.max) {
    difficultyMin.value = null
    difficultyMax.value = null
  } else {
    difficultyMin.value = p.min
    difficultyMax.value = p.max
  }
  page.value = 1
  fetchProblems()
}

function onSearch() {
  page.value = 1
  fetchProblems()
}

function onPageChange(p) {
  page.value = p
  fetchProblems()
}

function statusLabel(s) {
  const map = { pending_new: '待审核', pending_modify: '重新审核',
                approved: '公开', rejected: '不通过', frozen: '冻结', archived: '归档' }
  return map[s] || s
}

function typeLabel(t) {
  const map = { traditional: '传统题', 'output-only': '输出题', interactive: '交互题', communication: '通信题' }
  return map[t] || t
}

function formatK(n) {
  if (n == null || n === 0) return '0'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

function statusBadgeClass(s) {
  const map = { approved: 'badge-success', pending_new: 'badge-warning', pending_modify: 'badge-warning',
                rejected: 'badge-danger',
                frozen: 'badge-info', archived: 'badge-danger' }
  return map[s] || 'badge-info'
}

function applyQuery() {
  const q = route.query
  if (q.status) status.value = q.status
  if (q.keyword) keyword.value = q.keyword
  if (q.sort_by) sortBy.value = q.sort_by
  if (q.sort_order) sortOrder.value = q.sort_order
  if (q.problem_type) problemType.value = q.problem_type
  if (q.review_mode === 'true') reviewMode.value = true
  if (q.hide_solved === 'true') hideSolved.value = true
}

watch(() => route.query, () => {
  applyQuery()
  page.value = 1
  fetchProblems()
})

onMounted(() => {
  applyQuery()
  fetchProblems()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1>
        题库
        <span v-if="auth.isAdmin && reviewCount > 0" class="review-count-badge">{{ reviewCount }} 待审</span>
        <span v-if="auth.isAdmin && reviewCount === 0 && !loading" class="review-done text-sm text-muted" title="当前已无题目需要审核">✓ 无待审</span>
      </h1>
      <router-link v-if="auth.isLoggedIn" to="/problems/create" class="btn btn-primary">上传题目</router-link>
    </div>

    <!-- Filters -->
    <div class="card" style="padding:16px">
      <div class="flex flex-wrap gap-1 mb-2">
        <input v-model="keyword" class="form-input" style="max-width:200px" placeholder="搜索题名..." @keyup.enter="onSearch" />
        <button class="btn btn-primary btn-sm" @click="onSearch">搜索</button>
        <select v-model="problemType" class="form-select" style="max-width:150px" @change="onSearch">
          <option value="">全部类型</option>
          <option value="traditional">传统题</option>
          <option value="interactive">交互题</option>
          <option value="output-only">输出题</option>
          <option value="communication">通信题</option>
        </select>
        <select v-if="auth.isAdmin" v-model="status" class="form-select" style="max-width:110px" @change="onSearch">
          <option value="">全部状态</option>
          <option value="pending_new">待审核</option>
          <option value="pending_modify">重新审核</option>
          <option value="approved">公开</option>
          <option value="rejected">不通过</option>
          <option value="frozen">冻结</option>
          <option value="archived">归档</option>
        </select>
        <select v-model="sortBy" class="form-select" style="max-width:140px" @change="onSearch">
          <option value="problem_number">按编号</option>
          <option value="difficulty">按难度</option>
          <option value="accepted_count">按通过数</option>
          <option value="created_at">按时间</option>
        </select>
        <button class="btn btn-outline btn-sm" @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'; onSearch()">
          {{ sortOrder === 'asc' ? '↑ 升序' : '↓ 降序' }}
        </button>
        <label v-if="auth.isLoggedIn" class="flex gap-1" style="align-items:center;cursor:pointer;margin-left:8px">
          <input type="checkbox" v-model="hideSolved" @change="onSearch" />
          <span class="text-sm">隐藏已通过</span>
        </label>
      </div>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="p in presets" :key="p.label"
          class="btn btn-sm"
          :class="difficultyMin === p.min && difficultyMax === p.max ? 'btn-primary' : 'btn-outline'"
          @click="applyPreset(p)"
        >{{ p.label }}</button>
      </div>
    </div>

    <!-- Problem Table -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="problems.length === 0" class="card empty-state">
      <p>暂无题目</p>
    </div>
    <div v-else class="card table-container" style="padding:0">
      <table>
        <thead>
          <tr>
            <th>编号</th>
            <th>题名</th>
            <th>类型</th>
            <th>难度</th>
            <th v-if="auth.isAdmin">状态</th>
            <th>标签</th>
            <th>通过/提交</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in problems" :key="p.problem_id">
            <td :class="{ 'text-success': p.is_solved }">
              <router-link :to="`/problems/${p.problem_number || 'p' + p.problem_id}`" target="_blank" class="plain-link">
                {{ p.problem_number || '#' + p.problem_id }}
              </router-link>
            </td>
            <td>
              <router-link :to="`/problems/${p.problem_number || 'p' + p.problem_id}`" target="_blank" class="plain-link">
                <strong :class="{ 'text-success': p.is_solved }">{{ p.problem_name }}</strong>
              </router-link>
            </td>
            <td><span class="tag tag-sm">{{ typeLabel(p.problem_type) }}</span></td>
            <td>{{ p.difficulty }}</td>
            <td v-if="auth.isAdmin">
              <span class="badge" :class="statusBadgeClass(p.problem_status)">{{ statusLabel(p.problem_status) }}</span>
            </td>
            <td class="tags-cell">
              <span v-for="t in (p.tags || [])" :key="t" class="tag tag-sm">{{ t }}</span>
            </td>
            <td>{{ formatK(p.accepted_user_count) }}/{{ formatK(p.submission_count) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination :page="page" :size="size" :total="total" @change="onPageChange" />
  </div>
</template>

<style scoped>
td a { display: block; margin: -10px -14px; padding: 10px 14px; color: inherit; text-decoration: none; }
td a:hover { color: var(--primary); }
.tags-cell { overflow: hidden; max-height: 2.8em; line-height: 1.4; }
.review-count-badge {
  display: inline-block; font-size: 12px; font-weight: 600;
  background: #fef3c7; color: #92400e;
  padding: 2px 10px; border-radius: 12px; margin-left: 10px;
  vertical-align: middle;
}
.review-done { margin-left: 10px; }
</style>
