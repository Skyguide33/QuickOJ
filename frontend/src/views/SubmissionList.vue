<script setup>
import { ref, onMounted, onUnmounted, onActivated, onDeactivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { submissionsApi } from '../api/submissions'
import { formatTimeShort } from '../utils/time'
import Pagination from '../components/Pagination.vue'
import { CONFIG } from '../config'
defineOptions({ name: 'SubmissionList' })

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const submissions = ref([])
const total = ref(0)
const loading = ref(true)

const page = ref(1)
const size = 20
const problemNumber = ref('')
const username = ref('')
const language = ref('')
const status = ref('')
const isTestRun = ref(null)  // null=全部, 0=正式, 1=审核
const orderBy = ref('submitted_at')
const order = ref('desc')
const autoRefresh = ref(false)
let refreshTimer = null

async function fetchSilent() {
  if (document.hidden) return
  try {
    const params = { page: page.value, size, order_by: orderBy.value, order: order.value }
    if (problemNumber.value) params.problem_number = problemNumber.value
    if (username.value) params.username = username.value
    if (language.value) params.language = language.value
    if (status.value) params.status = status.value
    if (isTestRun.value !== null) params.is_test_run = isTestRun.value
    const res = await submissionsApi.getList(params, true) // skipCache: 实时刷新必须拿到最新数据
    if (res.code === 0) {
      const newList = res.data.list
      const newTotal = res.data.pagination.total
      // 对比 ID + status 判断是否有变化
      const changed = newTotal !== total.value
        || newList.length !== submissions.value.length
        || newList.some((s, i) => s.submission_id !== submissions.value[i]?.submission_id
                                  || s.status !== submissions.value[i]?.status)
      if (changed) {
        submissions.value = newList
        total.value = newTotal
      }
    }
  } catch { /* ignore */ }
}

watch(autoRefresh, (val) => {
  if (val) {
    refreshTimer = setInterval(fetchSilent, CONFIG.SUBMISSION_REFRESH_INTERVAL)
  } else {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})

function onVisChange() {
  if (!document.hidden && autoRefresh.value) fetchSilent()
}
onMounted(() => document.addEventListener('visibilitychange', onVisChange))
onUnmounted(() => {
  clearInterval(refreshTimer)
  document.removeEventListener('visibilitychange', onVisChange)
})
// keep-alive: 切走时暂停定时器，切回时恢复
onDeactivated(() => {
  clearInterval(refreshTimer)
  refreshTimer = null
})
onActivated(() => {
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchSilent, CONFIG.SUBMISSION_REFRESH_INTERVAL)
  }
})

const statusOptions = [
  'accepted', 'presentation_error', 'wrong_answer',
  'time_limit_exceeded', 'memory_limit_exceeded',
  'runtime_error', 'compile_error', 'system_error', 'rj',
  'pending', 'compiling', 'running',
]

function statusText(s) {
  const map = {
    accepted: 'AC', presentation_error: 'PE', wrong_answer: 'WA',
    time_limit_exceeded: 'TLE', memory_limit_exceeded: 'MLE',
    runtime_error: 'RE', compile_error: 'CE', system_error: 'SE', rj: 'RJ',
    pending: 'PD', compiling: 'CP', running: 'RN',
    'Accepted': 'AC', 'Presentation Error': 'PE', 'Wrong Answer': 'WA',
    'Time Limit Exceeded': 'TLE', 'Memory Limit Exceeded': 'MLE',
    'Runtime Error': 'RE', 'Compile Error': 'CE', 'System Error': 'SE',
  }
  return map[s] || s
}

function statusClass(s) {
  return `status-${(s || '').replace(/_/g, '-')}`
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, size, order_by: orderBy.value, order: order.value }
    if (problemNumber.value) params.problem_number = problemNumber.value
    if (username.value) params.username = username.value
    if (language.value) params.language = language.value
    if (status.value) params.status = status.value
    if (isTestRun.value !== null) params.is_test_run = isTestRun.value

    const res = await submissionsApi.getList(params)
    if (res.code === 0) {
      submissions.value = res.data.list
      total.value = res.data.pagination.total
    }
  } catch { /* ignore */ }
  loading.value = false
}

function onSearch() { page.value = 1; fetchData() }
function onPageChange(p) { page.value = p; fetchData() }

function applyQuery() {
  const q = route.query
  if (q.problem_number) problemNumber.value = q.problem_number
  if (q.username) username.value = q.username
  if (q.status) status.value = q.status
  if (q.language) language.value = q.language
}

watch(() => route.query, () => { applyQuery(); page.value = 1; fetchData() })

onMounted(() => {
  applyQuery()
  fetchData()
})
</script>

<template>
  <div>
    <div class="page-header"><h1>提交记录</h1></div>

    <div class="card" style="padding:16px">
      <div class="flex flex-wrap gap-1">
        <input v-model="problemNumber" class="form-input" style="max-width:120px" placeholder="题号" @keyup.enter="onSearch" />
        <input v-model="username" class="form-input" style="max-width:140px" placeholder="用户名/ID" @keyup.enter="onSearch" />
        <button class="btn btn-primary btn-sm" @click="onSearch">搜索</button>
        <select v-model="language" class="form-select" style="max-width:120px" @change="onSearch">
          <option value="">全部语言</option>
          <option value="cpp">C++</option>
          <option value="python3">Python3</option>
        </select>
        <select v-model="status" class="form-select" style="max-width:120px" @change="onSearch">
          <option value="">全部状态</option>
          <option v-for="s in statusOptions" :key="s" :value="s">{{ statusText(s) }}</option>
        </select>
        <select v-if="auth.isAdmin" v-model="isTestRun" class="form-select" style="max-width:110px" @change="onSearch">
          <option :value="null">全部记录</option>
          <option :value="0">正式提交</option>
          <option :value="1">审核提交</option>
        </select>
        <select v-model="orderBy" class="form-select" style="max-width:140px" @change="onSearch">
          <option value="submitted_at">按时间</option>
          <option value="run_time">按运行时间</option>
          <option value="run_memory">按内存</option>
          <option value="code_length">按代码长度</option>
        </select>
        <button class="btn btn-outline btn-sm" @click="order = order === 'asc' ? 'desc' : 'asc'; onSearch()">
          {{ order === 'asc' ? '↑' : '↓' }}
        </button>
        <label class="flex gap-1" style="align-items:center;cursor:pointer;margin-left:8px">
          <input type="checkbox" v-model="autoRefresh" />
          <span class="text-sm">实时刷新</span>
        </label>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="card table-container" style="padding:0">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>题目</th>
            <th>用户</th>
            <th>语言</th>
            <th>状态</th>
            <th>时间</th>
            <th>内存</th>
            <th>提交时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in submissions" :key="s.submission_id"
              :class="{ 'test-run': s.is_test_run }">
            <td>
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">
                #{{ s.submission_id }}
              </router-link>
            </td>
            <td>
              <router-link :to="`/problems/${s.problem_number || 'p' + s.problem_id}`">
                {{ s.problem_number || '#' + s.problem_id }} {{ s.problem_name }}
              </router-link>
            </td>
            <td>
              <router-link :to="`/user/${s.user_id}`" class="plain-link">{{ s.username }}</router-link>
            </td>
            <td>
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">
                <span class="tag tag-sm">{{ s.language }}</span>
              </router-link>
            </td>
            <td>
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">
                <strong :class="statusClass(s.status)">{{ statusText(s.status) }}</strong>
              </router-link>
            </td>
            <td class="text-sm">
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">{{ s.run_time || '-' }}ms</router-link>
            </td>
            <td class="text-sm">
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">{{ s.run_memory ? (s.run_memory / 1024).toFixed(1) + 'MB' : '-' }}</router-link>
            </td>
            <td class="text-sm text-muted">
              <router-link :to="`/submissions/${s.submission_id}`" target="_blank" class="plain-link">{{ formatTimeShort(s.submitted_at) }}</router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination :page="page" :size="size" :total="total" @change="onPageChange" />
  </div>
</template>

<style scoped>
.test-run { background: #eff6ff; }
.test-run:hover td { background: #dbeafe !important; }
td a {
  display: block; margin: -10px -14px; padding: 10px 14px;
  color: inherit; text-decoration: none; white-space: nowrap;
}
td a:hover { color: var(--primary); }
</style>
