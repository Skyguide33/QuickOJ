<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { formatDate } from '../utils/time'
import { problemsApi } from '../api/problems'
import { adminApi } from '../api/admin'
import { CONFIG } from '../config'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import CodeEditor from '../components/CodeEditor.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const problem = ref(null)
const loading = ref(true)
const errorMsg = ref('')
const adminMsg = ref(null)

const reviewModal = ref(null)  // 'approved' | 'rejected'
const reviewReason = ref('')
const reviewLoading = ref(false)

function openReviewModal(action) {
  reviewReason.value = ''
  adminMsg.value = null
  reviewModal.value = action
}

async function confirmReview() {
  if (reviewModal.value === 'rejected' && !reviewReason.value.trim()) {
    adminMsg.value = { type: 'error', text: '拒绝时必须填写原因' }
    return
  }
  reviewLoading.value = true
  adminMsg.value = null
  try {
    const res = await adminApi.changeProblemStatus(
      problem.value.problem_id,
      reviewModal.value,
      reviewReason.value || undefined,
    )
    if (res.code === 0) {
      reviewModal.value = null
      fetchProblem()
    } else {
      adminMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    adminMsg.value = { type: 'error', text: e.message }
  }
  reviewLoading.value = false
}

const manageModal = ref(null)  // 'approved' | 'frozen' | 'archived' | 'delete'
const manageLoading = ref(false)

function openManageModal(action) {
  adminMsg.value = null
  manageModal.value = action
}

async function confirmManageAction() {
  const action = manageModal.value
  manageLoading.value = true
  adminMsg.value = null
  const problemId = problem.value.problem_id
  try {
    if (problem.value.has_pending_data && !reviewComment.value.trim()) {
      await adminApi.changeProblemStatus(problemId, 'rejected', '管理员在管理操作中自动拒绝')
    }
    if (action === 'delete') {
      const res = await problemsApi.delete(problemId)
      if (res.code === 0) { router.push('/problems'); return }
      adminMsg.value = { type: 'error', text: res.message }
    } else {
      const res = await adminApi.changeProblemStatus(problemId, action, reviewComment.value || undefined)
      if (res.code === 0) {
        manageModal.value = null
        reviewComment.value = ''
        fetchProblem()
      } else {
        adminMsg.value = { type: 'error', text: res.message }
      }
    }
  } catch (e) { adminMsg.value = { type: 'error', text: e.message } }
  manageLoading.value = false
}

const manageLabels = { approved: '恢复公开', frozen: '冻结', archived: '归档', delete: '删除' }
const manageDescs = {
  approved: '将题目恢复为公开状态，所有人可见。',
  frozen: '冻结题目，仅管理员可见，禁止提交。',
  archived: '归档题目，永久下架。',
  delete: '彻底删除该题目及其所有数据，此操作不可撤销。',
}

// 管理弹窗中应显示的按钮
const manageButtons = computed(() => {
  const s = problem.value?.problem_status
  const btns = []
  if (s !== 'approved' && s !== 'pending_new' && s !== 'pending_modify') btns.push({ key: 'approved', label: '恢复公开' })
  if (s !== 'frozen') btns.push({ key: 'frozen', label: '冻结' })
  if (s !== 'archived') btns.push({ key: 'archived', label: '归档' })
  btns.push({ key: 'delete', label: '删除', danger: true })
  return btns
})

// Tab state
const activeTab = ref('statement')

// Submit
const code = ref('')
const language = ref('cpp')
const submitting = ref(false)
const submitResult = ref(null)
const usePending = ref(false)

// Debug
const debugInput = ref('')
const debugOutput = ref(null)
const debugging = ref(false)

const reviewComment = ref('')

// Polling for submission status
let pollTimer = null

async function handleChangeStatus(newStatus) {
  adminMsg.value = null
  adminLoading.value = true
  try {
    const res = await adminApi.changeProblemStatus(
      problem.value.problem_id, newStatus, reviewComment.value || undefined
    )
    if (res.code === 0) {
      adminMsg.value = { type: 'success', text: res.message }
      reviewComment.value = ''
      fetchProblem()
    } else {
      adminMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    adminMsg.value = { type: 'error', text: e.message }
  }
  adminLoading.value = false
}

async function handleDelete() {
  if (!confirm('确定要删除这道题目吗？此操作不可撤销。')) return
  adminMsg.value = null
  adminLoading.value = true
  try {
    const res = await problemsApi.delete(route.params.id)
    if (res.code === 0) {
      router.push('/problems')
    } else {
      adminMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    adminMsg.value = { type: 'error', text: e.message }
  }
  adminLoading.value = false
}

function typeLabel(t) {
  const map = { traditional: '传统题', 'output-only': '输出题', interactive: '交互题', communication: '通信题' }
  return map[t] || t
}

function statusLabel(s) {
  const map = {
    pending_new: '待审核', pending_modify: '重新审核',
    approved: '公开', rejected: '不通过', frozen: '冻结', archived: '归档'
  }
  return map[s] || s
}

function statusBadgeClass(s) {
  const map = {
    approved: 'badge-success', pending_new: 'badge-warning', pending_modify: 'badge-warning',
    rejected: 'badge-danger', frozen: 'badge-info', archived: 'badge-danger'
  }
  return map[s] || 'badge-info'
}

async function fetchProblem() {
  loading.value = true
  try {
    const res = await problemsApi.getDetail(route.params.identifier)
    if (res.code === 0) {
      problem.value = res.data
      if (res.data.is_new_problem) usePending.value = true
      const label = res.data.problem_number || '#' + res.data.problem_id
      document.title = `${label} ${res.data.problem_name} - QuickOJ`
    } else {
      errorMsg.value = res.message
    }
  } catch (e) {
    errorMsg.value = e.message
  }
  loading.value = false
}

async function handleSubmit() {
  if (!code.value.trim()) return
  submitting.value = true
  submitResult.value = null
  try {
    const fd = new FormData()
    fd.append('code', code.value)
    fd.append('language', language.value)
    if (usePending.value) fd.append('use_pending', 'true')
    const res = await problemsApi.submit(problem.value.problem_id, fd)
    if (res.code === 0) {
      submitResult.value = { type: 'success', msg: `提交成功！提交ID: ${res.data.submission_id}` }
      // Navigate to submission detail
      router.push(`/submissions/${res.data.submission_id}`)
    } else {
      submitResult.value = { type: 'error', msg: res.message }
    }
  } catch (e) {
    submitResult.value = { type: 'error', msg: e.message }
  }
  submitting.value = false
}

async function handleDebug() {
  if (!code.value.trim()) return
  if (debugInput.value.length > 500000) {
    debugOutput.value = { status: 'Input Error', error: '输入的数据过大' }
    return
  }
  debugging.value = true
  debugOutput.value = null
  try {
    const fd = new FormData()
    fd.append('code', code.value)
    fd.append('language', language.value)
    fd.append('input_data', debugInput.value)
    const res = await problemsApi.debug(problem.value.problem_id, fd)
    if (res.code !== 0 || !res.data?.job_id) {
      debugOutput.value = { status: 'error', output: res.message || '提交失败' }
      debugging.value = false
      return
    }
    // 轮询等待调试结果
    const jobId = res.data.job_id
    const poll = setInterval(async () => {
      try {
        const r = await problemsApi.getDebugResult(jobId)
        if (r.code === 0 && r.data?.status && r.data.status !== 'pending') {
          clearInterval(poll)
          debugOutput.value = r.data.status === 'system_error'
            ? { status: 'system_error', output: r.data.error || '评测机离线' }
            : r.data
          debugging.value = false
        }
      } catch { /* retry */ }
    }, CONFIG.DEBUG_POLL_INTERVAL)
  } catch (e) {
    debugOutput.value = { error: e.message, status: 'error' }
    debugging.value = false
  }
}

const langOptions = [
  { value: 'cpp', label: 'C++' },
  { value: 'python3', label: 'Python 3' },
]

const langTemplates = {
  cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}',
  python3: '# 在此编写代码\n',
}

function setLanguage(lang) {
  language.value = lang
  if (!code.value.trim()) {
    code.value = langTemplates[lang] || ''
  }
}

onMounted(() => {
  setLanguage('cpp')
  fetchProblem()
})
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>

  <div v-else-if="errorMsg" class="card">
    <div class="alert alert-error">{{ errorMsg }}</div>
    <router-link to="/problems" class="btn btn-outline">← 返回题库</router-link>
  </div>

  <div v-else-if="problem" class="problem-detail">
    <!-- Header -->
    <div class="card">
      <div class="flex-between flex-wrap gap-2">
        <div>
          <h1 style="font-size:22px">
            <span v-if="problem.user_status?.is_solved" class="solved-check" title="已通过">✓</span>
            {{ problem.problem_number || '#' + problem.problem_id }} {{ problem.problem_name }}
            <span v-if="auth.isAdmin || problem.uploader?.user_id === auth.user?.user_id" class="badge ml-1" :class="statusBadgeClass(problem.problem_status)">
              {{ statusLabel(problem.problem_status) }}
            </span>
            <span v-if="auth.isAdmin && problem.is_new_problem" class="badge ml-1" style="background:#dbeafe;color:#1e40af">NEW</span>
          </h1>
          <div class="mt-1 flex flex-wrap gap-1">
            <span class="badge badge-info">{{ typeLabel(problem.problem_type) }}</span>
            <span class="text-muted text-sm">难度: {{ problem.difficulty }}</span>
            <span class="text-muted text-sm">时间限制: {{ problem.time_limit }}ms</span>
            <span class="text-muted text-sm">内存限制: {{ (problem.memory_limit / 1024).toFixed(0) }}MB</span>
          </div>
        </div>
        <div class="flex gap-1">
          <router-link v-if="(auth.isAdmin || problem.uploader?.user_id === auth.user?.user_id) && problem.problem_status !== 'pending_new' && problem.problem_status !== 'pending_modify'"
            :to="`/problems/${problem.problem_number || 'p' + problem.problem_id}/edit`" class="btn btn-outline btn-sm">编辑</router-link>
          <template v-if="auth.isAdmin">
            <button v-for="b in manageButtons" :key="b.key"
              :class="b.danger ? 'btn btn-danger btn-sm' : 'btn btn-outline btn-sm'"
              @click="openManageModal(b.key)">{{ b.label }}</button>
          </template>
          <router-link
            :to="`/submissions?problem_number=${auth.isAdmin ? '%23' + problem.problem_id : (problem.problem_number || '%23' + problem.problem_id)}`"
            class="btn btn-primary">提交记录</router-link>
        </div>
      </div>
      <div class="mt-2 text-sm text-muted">
        上传者:
        <router-link v-if="problem.uploader?.user_id"
          :to="`/user/${problem.uploader.user_id}`">
          {{ problem.uploader.username }}
        </router-link>
        <span v-else>{{ problem.uploader?.username }}</span>
        · 来源: {{ problem.source || '原创' }}
        · 通过人数: {{ problem.statistics?.accepted_user_count || 0 }}
        · 创建于 {{ formatDate(problem.created_at) }}
        <span v-if="problem.tags?.length" class="ml-1">
          · 标签:
          <span v-for="t in problem.tags" :key="t" class="tag tag-sm">{{ t }}</span>
        </span>
      </div>

      <!-- Admin action bar: 仅待审核时可见 -->
      <div v-if="auth.isAdmin && (problem.problem_status === 'pending_new' || problem.problem_status === 'pending_modify')" class="admin-bar mt-2">
        <div v-if="adminMsg" :class="adminMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'" style="margin-bottom:12px">
          {{ adminMsg.text }}
        </div>
        <div class="flex flex-wrap gap-1" style="align-items:center">
          <span class="text-sm text-muted mr-1">审核操作:</span>
          <button class="btn btn-success btn-sm"
            @click="openReviewModal('approved')">审核通过</button>
          <button class="btn btn-danger btn-sm"
            @click="openReviewModal('rejected')">拒绝</button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="card" style="padding:0">
      <div class="tabs">
        <button :class="{ active: activeTab === 'statement' }" @click="activeTab = 'statement'">题目描述</button>
        <button v-if="auth.isLoggedIn && problem.problem_status !== 'rejected' && !(!auth.isAdmin && problem.uploader?.user_id === auth.user?.user_id && problem.problem_status === 'pending_new')"
          :class="{ active: activeTab === 'submit' }" @click="activeTab = 'submit'">提交与调试</button>
      </div>
    </div>

    <!-- Statement -->
    <div v-if="activeTab === 'statement'" class="card">
      <MarkdownRenderer :content="problem.statement || ''" />

      <!-- Samples -->
      <div v-if="problem.sample_input" class="mt-2">
        <h3>样例输入</h3>
        <pre class="sample-block">{{ problem.sample_input }}</pre>
      </div>
      <div v-if="problem.sample_output" class="mt-1">
        <h3>样例输出</h3>
        <pre class="sample-block">{{ problem.sample_output }}</pre>
      </div>
    </div>

    <!-- Submit & Debug -->
    <div v-if="activeTab === 'submit' && auth.isLoggedIn" class="card">
      <h2 class="card-title">提交与调试</h2>
      <div v-if="submitResult" :class="submitResult.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
        {{ submitResult.msg }}
      </div>
      <div class="form-group">
        <label class="form-label">语言</label>
        <select v-model="language" class="form-select" style="max-width:200px" @change="setLanguage(language)">
          <option v-for="l in langOptions" :key="l.value" :value="l.value">{{ l.label }}</option>
        </select>
      </div>
      <div v-if="auth.isAdmin && problem.has_pending_data" class="form-group">
        <label class="flex gap-1" style="align-items:center;cursor:pointer">
          <input type="checkbox" v-model="usePending" :disabled="problem.is_new_problem" />
          <span class="badge badge-warning">管理员测试</span>
          使用待审核的新测试数据（提交记录仅管理员可见）
          <span v-if="problem.is_new_problem" class="text-sm text-muted">（新题目强制勾选）</span>
        </label>
      </div>
      <div class="form-group">
        <label class="form-label">代码</label>
        <CodeEditor v-model="code" :language="language" :tab-size="4" />
      </div>
      <div class="flex gap-1 mt-2">
        <button class="btn btn-primary" :disabled="debugging || !code.trim()" @click="handleDebug">
          {{ debugging ? '运行中...' : '运行调试' }}
        </button>
        <button class="btn btn-success" :disabled="submitting || !code.trim()" @click="handleSubmit">
          {{ submitting ? '提交中...' : '提交评测' }}
        </button>
      </div>

      <div class="io-row mt-2">
        <div class="io-col">
          <label class="form-label">自定义输入 <span class="text-muted">（调试用）</span>
            <span class="text-sm text-muted" style="float:right">{{ debugInput.length }}/500000</span>
          </label>
          <textarea v-model="debugInput" class="form-textarea" rows="8" maxlength="500000"
            placeholder="输入测试数据（最多 500000 字符）..."></textarea>
        </div>
        <div class="io-col">
          <label class="form-label">运行结果
            <span v-if="debugOutput && debugOutput.status === 'ok'" class="text-success text-sm"> — 运行成功</span>
            <span v-else-if="debugOutput && debugOutput.status === 'compile_error'" class="text-sm" style="color:#a16207"> — CE</span>
            <span v-else-if="debugOutput && debugOutput.status === 'time_limit_exceeded'" class="text-sm" style="color:#2563a0"> — TLE</span>
            <span v-else-if="debugOutput && debugOutput.status === 'memory_limit_exceeded'" class="text-sm" style="color:#2563a0"> — MLE</span>
            <span v-else-if="debugOutput && debugOutput.status === 'runtime_error'" class="text-sm" style="color:#7c3aed"> — RE</span>
            <span v-else-if="debugOutput && debugOutput.status === 'system_error'" class="text-sm" style="color:#1f2937"> — SE</span>
            <span v-else-if="debugOutput && debugOutput.status === 'Input Error'" class="text-sm" style="color:var(--danger)"> — 输入过大</span>
            <span v-if="debugOutput && debugOutput.run_time != null" class="text-sm text-muted"> · {{ debugOutput.run_time }}ms</span>
            <span v-if="debugOutput && debugOutput.run_memory != null" class="text-sm text-muted"> · {{ debugOutput.run_memory }}KB</span>
          </label>
          <pre v-if="debugOutput" class="sample-block" style="flex:1;overflow:auto;min-height:0;height:0;white-space:pre-wrap">{{
            debugOutput.compile_error || debugOutput.output || debugOutput.error || debugOutput.message || ''
          }}</pre>
          <div v-else class="text-sm text-muted result-placeholder">点击运行调试查看结果</div>
        </div>
      </div>
    </div>
    <div v-else-if="activeTab === 'submit'" class="card empty-state">
      <p>请先 <router-link to="/login">登录</router-link> 后提交代码</p>
    </div>

    <!-- 审核确认弹窗 -->
    <div v-if="reviewModal" class="modal-overlay" @click.self="reviewModal = null">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>{{ reviewModal === 'approved' ? '确认审核通过' : '确认拒绝' }}</h3>
          <button class="btn btn-outline btn-sm" @click="reviewModal = null">✕</button>
        </div>
        <div v-if="adminMsg" :class="adminMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
          {{ adminMsg.text }}
        </div>
        <p class="text-sm text-muted mb-2">
          {{ reviewModal === 'approved' ? '确定要将该题目审核通过吗？通过后题目将公开可见。' : '请填写拒绝原因：' }}
        </p>
        <div v-if="reviewModal === 'rejected'" class="form-group">
          <textarea v-model="reviewReason" class="form-textarea" rows="4" placeholder="请详细说明拒绝原因，将通知上传者..."></textarea>
        </div>
        <div class="flex gap-1">
          <button class="btn btn-outline" @click="reviewModal = null">取消</button>
          <button :class="reviewModal === 'approved' ? 'btn btn-success' : 'btn btn-danger'"
            :disabled="reviewLoading" @click="confirmReview">
            {{ reviewLoading ? '处理中...' : (reviewModal === 'approved' ? '确认通过' : '确认拒绝') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 管理确认弹窗 -->
    <div v-if="manageModal" class="modal-overlay" @click.self="manageModal = null">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>确认{{ manageLabels[manageModal] }}</h3>
          <button class="btn btn-outline btn-sm" @click="manageModal = null">✕</button>
        </div>
        <div v-if="adminMsg" :class="adminMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
          {{ adminMsg.text }}
        </div>
        <p class="text-sm text-muted mb-2">{{ manageDescs[manageModal] }}</p>
        <div v-if="problem.has_pending_data && !reviewComment.trim()" class="text-sm text-muted mb-2">
          注意：未填写审核备注，操作前将自动拒绝待审核数据。
        </div>
        <div class="flex gap-1">
          <button class="btn btn-outline" @click="manageModal = null">取消</button>
          <button :class="manageModal === 'delete' ? 'btn btn-danger' : 'btn btn-primary'"
            :disabled="manageLoading" @click="confirmManageAction">
            {{ manageLoading ? '处理中...' : '确认' + manageLabels[manageModal] }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  border-bottom: 2px solid var(--gray-200);
}
.tabs button {
  padding: 12px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  color: var(--gray-600);
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all .15s;
}
.tabs button:hover { color: var(--primary); }
.tabs button.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}
.sample-block {
  background: #f6f8fa;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 13px;
  font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  line-height: 1.5;
}
.solved-check {
  color: var(--success); font-size: 18px; font-weight: 700;
  margin-right: -2px; vertical-align: middle;
}
.io-row { display: flex; gap: 16px; align-items: stretch; }
.io-col { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.io-col .form-textarea, .io-col .sample-block, .io-col .result-placeholder {
  flex: 1; min-height: 180px; max-height: 300px; overflow-y: auto;
}
.result-placeholder {
  border: 1px solid var(--gray-200); border-radius: var(--radius);
  padding: 12px; display: flex; align-items: center; justify-content: center;
  color: var(--gray-400);
}
.debug-result { border-top: 1px solid var(--gray-200); padding-top: 16px; }
.admin-bar { border-top: 1px solid var(--gray-200); padding-top: 16px; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-card {
  background: #fff; border-radius: var(--radius); padding: 24px;
  width: 360px; max-width: 90vw; box-shadow: var(--shadow-md);
}
.ml-1 { margin-left: 8px; }
.mr-1 { margin-right: 8px; }
</style>
