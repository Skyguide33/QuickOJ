<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { formatTimeShort } from '../utils/time'
import { submissionsApi } from '../api/submissions'
import { CONFIG } from '../config'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const route = useRoute()

const submission = ref(null)
const loading = ref(true)
const errorMsg = ref('')

let pollTimer = null
let pollStart = 0
let pollExpired = false
const FINAL_STATES = ['accepted', 'presentation_error', 'wrong_answer', 'time_limit_exceeded',
  'memory_limit_exceeded', 'runtime_error', 'compile_error', 'system_error', 'rj']
function isFinal(s) { return FINAL_STATES.includes(s) }

function statusFull(s) {
  const map = {
    accepted: 'Accepted', presentation_error: 'Presentation Error',
    wrong_answer: 'Wrong Answer', time_limit_exceeded: 'Time Limit Exceeded',
    memory_limit_exceeded: 'Memory Limit Exceeded', runtime_error: 'Runtime Error',
    compile_error: 'Compile Error', system_error: 'System Error',
    rj: 'Rejected', pending: 'Pending', compiling: 'Compiling', running: 'Running',
  }
  return map[s] || s
}

function statusClass(s) {
  return `status-${(s || '').replace(/_/g, '-')}`
}
function statusText(s) {
  const map = {
    accepted: 'AC', presentation_error: 'PE', wrong_answer: 'WA',
    time_limit_exceeded: 'TLE', memory_limit_exceeded: 'MLE',
    runtime_error: 'RE', compile_error: 'CE',
    pending: 'Pending', compiling: 'Compiling', running: 'Running', system_error: 'SE',
    'System Error': 'SE', 'Runtime Error': 'RE', 'Compile Error': 'CE',
    'Time Limit Exceeded': 'TLE', 'Memory Limit Exceeded': 'MLE',
    'Wrong Answer': 'WA', 'Presentation Error': 'PE', 'Accepted': 'AC',
    'Pending': '...',
  }
  return map[s] || s
}
function tpClass(status) {
  // 测试点颜色: AC绿, WA浅红, RE紫, TLE/MLE深蓝, CE黄, SE黑, Pending灰
  const m = {
    'Accepted': 'tp-ac', 'Presentation Error': 'tp-pe', 'Wrong Answer': 'tp-wa',
    'Time Limit Exceeded': 'tp-tle', 'Memory Limit Exceeded': 'tp-tle',
    'Runtime Error': 'tp-re', 'Compile Error': 'tp-ce',
    'System Error': 'tp-se', 'Rejected': 'tp-rj', 'Pending': 'tp-pending',
  }
  return m[status] || 'tp-default'
}

async function fetchDetail() {
  try {
    const res = await submissionsApi.getDetail(route.params.id)
    if (res.code === 0) {
      submission.value = res.data
      document.title = `提交 #${res.data.submission_id} - QuickOJ`
    } else {
      errorMsg.value = res.message || '加载失败'
    }
  } catch (e) {
    errorMsg.value = e.message === 'Network Error' ? '无法连接服务器，请检查网络' : (e.message || '加载失败')
  }
  loading.value = false
}

function startPolling() {
  if (!submission.value || isFinal(submission.value.status)) return
  pollStart = Date.now()
  pollExpired = false
  pollTimer = setInterval(async () => {
    if (Date.now() - pollStart >= CONFIG.SUBMISSION_DETAIL_POLL_TIMEOUT) { clearInterval(pollTimer); pollTimer = null; pollExpired = true; return }
    try {
      const res = await submissionsApi.getStatus(route.params.id)
      if (res.code === 0) {
        submission.value.status = res.data.status
        submission.value.run_time = res.data.run_time
        submission.value.run_memory = res.data.run_memory
        submission.value.judged_at = res.data.judged_at
        // 将完成的测试点合并到已有列表，或按 total_count 初始化全部 Pending 网格
        const done = res.data.judged_result || []
        const total = res.data.total_count || done.length
        if (!submission.value.judged_result && total > 0) {
          // 首次拿到 total_count：初始化全部 Pending 占位
          submission.value.judged_result = Array.from({length: total}, (_, i) =>
            ({name: String(i + 1), status: 'Pending', time_used: null, memory_used_kb: 0}))
        }
        if (submission.value.judged_result) {
          const merged = [...submission.value.judged_result]
          for (const d of done) {
            const idx = merged.findIndex(t => t.name === d.name)
            if (idx >= 0) merged[idx] = d
          }
          submission.value.judged_result = merged
        }
        if (isFinal(res.data.status)) { clearInterval(pollTimer); pollTimer = null }
      }
    } catch { /* ignore */ }
  }, CONFIG.SUBMISSION_DETAIL_POLL_INTERVAL)
}
async function onVis() {
  if (document.hidden) {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  } else {
    if (!submission.value || isFinal(submission.value.status)) return
    // 回到前台：轻量请求状态，不重复拉取代码
    try {
      const res = await submissionsApi.getStatus(route.params.id)
      if (res.code === 0) {
        submission.value.status = res.data.status
        submission.value.run_time = res.data.run_time
        submission.value.run_memory = res.data.run_memory
        submission.value.judged_at = res.data.judged_at
        // 合并完成的测试点到已有网格
        const done = res.data.judged_result || []
        if (done.length && submission.value.judged_result) {
          const merged = [...submission.value.judged_result]
          for (const d of done) {
            const idx = merged.findIndex(t => t.name === d.name)
            if (idx >= 0) merged[idx] = d
          }
          submission.value.judged_result = merged
        }
      }
    } catch { /* ignore */ }
    if (!pollExpired) startPolling()
  }
}

onMounted(async () => {
  await fetchDetail()
  startPolling()
  document.addEventListener('visibilitychange', onVis)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('visibilitychange', onVis)
})

const langMap = { cpp: 'cpp', python3: 'python' }
const highlightedCode = computed(() => {
  const code = submission.value?.code || ''
  const lang = langMap[submission.value?.language] || 'cpp'
  if (!code) return ''
  try {
    return hljs.highlight(code, { language: lang }).value
  } catch { return code.replace(/</g, '&lt;') }
})

const copyBtnText = ref('复制')
function copyCode() {
  const code = submission.value?.code || ''
  navigator.clipboard.writeText(code).then(() => {
    copyBtnText.value = '已复制'
    setTimeout(() => { copyBtnText.value = '复制' }, 1500)
  }).catch(() => {
    const ta = document.createElement('textarea')
    ta.value = code; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select()
    document.execCommand('copy'); document.body.removeChild(ta)
    copyBtnText.value = '已复制'
    setTimeout(() => { copyBtnText.value = '复制' }, 1500)
  })
}
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>

  <div v-else-if="errorMsg" class="card">
    <div class="alert alert-error">{{ errorMsg }}</div>
    <router-link to="/submissions" class="btn btn-outline">← 返回提交记录</router-link>
  </div>

  <div v-else-if="submission" class="submission-detail">
    <!-- Summary Card -->
    <div class="card">
      <div class="flex-between flex-wrap gap-2">
        <div>
          <h1 style="font-size:20px">
            提交 #{{ submission.submission_id }}
            <strong :class="statusClass(submission.status)">{{ statusFull(submission.status) }}</strong>
          </h1>
          <div class="mt-1 text-sm text-muted">
            题目: <router-link :to="`/problems/${submission.problem_number || 'p' + submission.problem_id}`">
              {{ submission.problem_number || '#' + submission.problem_id }} {{ submission.problem_name }}
            </router-link>
            · 用户: <router-link :to="`/user/${submission.user_id}`">{{ submission.username }}</router-link>
            · 语言: {{ submission.language }}
            · 时间: {{ submission.run_time || '-' }}ms
            · 内存: {{ submission.run_memory ? (submission.run_memory / 1024).toFixed(1) + 'MB' : '-' }}
            · 提交于 {{ formatTimeShort(submission.submitted_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Error / compile info -->
    <div v-if="submission.judged_error || submission.judged_compile" class="card">
      <div v-if="submission.judged_error" class="alert alert-error">
        <strong>评测错误:</strong>
        <pre class="error-block">{{ submission.judged_error }}</pre>
      </div>
      <div v-if="submission.judged_compile" class="mt-1">
        <strong>编译信息:</strong>
        <div class="text-sm text-muted">状态: {{ submission.judged_compile.status }}</div>
        <pre v-if="submission.judged_compile.output" class="error-block">{{ submission.judged_compile.output }}</pre>
      </div>
    </div>

    <!-- Test points (running 时显示全部测试点，未完成的灰色) -->
    <div v-if="submission.judged_result && submission.judged_result.length" class="card">
      <div v-if="submission.status === 'running'" class="mb-2 text-sm text-muted">
        ⏳ 评测中（{{ submission.judged_result.filter(t => t.status !== 'Pending').length }} / {{ submission.judged_result.length }}）
      </div>
      <h2 class="card-title">测试点详情</h2>
      <div class="testpoints">
        <div
          v-for="tp in submission.judged_result" :key="tp.name || tp.index"
          class="testpoint"
          :class="tpClass(tp.status)"
        >
          <span class="tp-index">#{{ tp.name || tp.index }}</span>
          <span class="tp-status">{{ statusText(tp.status) }}</span>
          <span class="tp-meta">
            {{ tp.time_used != null ? (tp.time_used * 1000).toFixed(0) + 'ms' : '-' }}
            ·
            {{ tp.memory_used_kb ? (tp.memory_used_kb >= 1024 ? (tp.memory_used_kb / 1024).toFixed(1) + 'MB' : tp.memory_used_kb + 'KB') : '-' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Source Code -->
    <div class="card">
      <h2 class="card-title">源代码</h2>
      <div class="code-wrap">
        <button class="copy-btn" @click="copyCode">{{ copyBtnText }}</button>
        <pre class="code-block"><code v-html="highlightedCode"></code></pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.testpoints {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}
.testpoint {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 6px;
  border: 1px solid var(--gray-200);
  font-size: 13px; background: var(--gray-50);
}
.tp-ac  { background: #dcfce7; border-color: #86efac; color: #166534; }  /* AC 浅绿 */
.tp-wa  { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }  /* WA 浅红 */
.tp-pe  { background: #e0f2fe; border-color: #7dd3fc; color: #075985; }  /* PE 浅蓝 */
.tp-re  { background: #f3e8ff; border-color: #c4b5fd; color: #6b21a8; }  /* RE 紫色 */
.tp-tle { background: #2563a0; border-color: #3b82f6; color: #eff6ff; }  /* TLE/MLE 蓝底白字 */
.tp-ce  { background: #fef9c3; border-color: #fde047; color: #854d0e; }  /* CE 黄底 */
.tp-se  { background: #1f2937; border-color: #374151; color: #f9fafb; }  /* SE 黑底白字 */
.tp-rj  { background: #7f1d1d; border-color: #991b1b; color: #fecaca; }  /* RJ 暗红底 */
.tp-default { background: var(--gray-100); border-color: var(--gray-300); color: var(--gray-600); }
.tp-pending { background: #f9fafb; border-color: #e5e7eb; color: #9ca3af; }  /* 灰色：等待评测 */
.tp-index { font-weight: 600; min-width: 28px; }
.tp-pending .tp-status { color: #9ca3af; }
.tp-status { font-weight: 600; }
.tp-meta { margin-left: auto; font-size: 12px; opacity: .7; }
.code-wrap { position: relative; }
.code-wrap .copy-btn {
  position: absolute; top: 8px; right: 12px; z-index: 1;
  padding: 2px 10px; font-size: 12px; font-family: inherit;
  background: var(--gray-100); color: var(--gray-600);
  border: 1px solid var(--gray-300); border-radius: 4px;
  cursor: pointer;
}
.code-wrap .copy-btn:hover { background: var(--gray-200); color: var(--gray-800); }
.code-block {
  background: #fafbfc;
  color: var(--gray-800);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius);
  padding: 16px;
  padding-top: 32px;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
  font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
}
.error-block {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 13px;
  font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  margin-top: 8px;
  line-height: 1.5;
}
</style>
