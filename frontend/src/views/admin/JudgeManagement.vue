<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { adminApi } from '../../api/admin'

const running = ref(false)
const connected = ref(false)
const statusText = ref('')
const cutoff = ref('')
const loading = ref(false)
const msg = ref(null)
const modal = ref(null)

function nowStr() {
  // datetime-local 输入框需要本地时间
  const d = new Date()
  const off = d.getTimezoneOffset()
  const local = new Date(d.getTime() - off * 60000)
  return local.toISOString().slice(0, 16)
}

function toUTC(localStr) {
  // 将本地时间字符串转为 UTC ISO 字符串
  const d = new Date(localStr)
  return d.toISOString().slice(0, 16)
}

async function fetchStatus(skipCache) {
  try {
    const res = await adminApi.getJudgeStatus(skipCache)
    if (res.code === 0) {
      running.value = res.data.running
      connected.value = res.data.connected
      statusText.value = res.data.status
    }
  } catch { /* ignore */ }
}

function openConnect() {
  cutoff.value = nowStr()
  msg.value = null
  modal.value = 'connect'
}

async function handleConnect() {
  loading.value = true; msg.value = null
  try {
    const utcCutoff = toUTC(cutoff.value)
    const res = await adminApi.connectJudge(utcCutoff)
    if (res.code === 0) { modal.value = null; fetchStatus() }
    else msg.value = { type: 'error', text: res.message }
  } catch (e) { msg.value = { type: 'error', text: e.message } }
  loading.value = false
}

async function handleDisconnect() {
  loading.value = true
  try {
    const res = await adminApi.disconnectJudge()
    if (res.code === 0) { modal.value = null; fetchStatus() }
    else msg.value = { type: 'error', text: res.message }
  } catch (e) { msg.value = { type: 'error', text: e.message } }
  loading.value = false
}

let timer = null
function startTimer() {
  if (timer) clearInterval(timer)
  timer = setInterval(() => fetchStatus(true), 2000)
}
function onVis() {
  if (document.hidden) { clearInterval(timer); timer = null }
  else { fetchStatus(true); startTimer() }
}
onMounted(() => {
  fetchStatus()
  startTimer()
  document.addEventListener('visibilitychange', onVis)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  document.removeEventListener('visibilitychange', onVis)
})
</script>

<template>
  <div>
    <div class="page-header"><h1>评测机管理</h1></div>

    <div v-if="msg" :class="msg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
      {{ msg.text }}
    </div>

    <div class="card text-center">
      <div class="mb-2">
        <span class="badge" :class="connected ? 'badge-success' : running ? 'badge-warning' : 'badge-danger'"
          style="font-size:16px;padding:6px 16px">
          {{ connected ? '● 已连接' : running ? '● 待连接' : '■ 未运行' }}
        </span>
      </div>
      <p class="text-sm text-muted mb-2">
        {{ connected ? 'OJ 已连接评测机，提交将被正常处理'
           : running ? '评测机服务已运行，但 OJ 尚未连接'
           : '评测机服务未运行，请在后台启动 judge_daemon.py' }}
      </p>
      <div class="flex gap-1" style="justify-content:center">
        <button v-if="running && !connected" class="btn btn-success" @click="openConnect">连接评测机</button>
        <button v-if="connected" class="btn btn-danger" @click="modal = 'disconnect'">断开连接</button>
      </div>
    </div>

    <!-- 连接弹窗 -->
    <div v-if="modal === 'connect'" class="modal-overlay" @click.self="modal = null">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>连接评测机</h3>
          <button class="btn btn-outline btn-sm" @click="modal = null">✕</button>
        </div>
        <div class="form-group">
          <label class="form-label">阈值时间（可选）</label>
          <input v-model="cutoff" type="datetime-local" class="form-input" />
          <p class="text-sm text-muted mt-1">早于此时间的 pending 提交将被标记为 RJ（拒绝评测）。默认当前时刻即全部继续。</p>
        </div>
        <div class="flex gap-1">
          <button class="btn btn-outline" @click="modal = null">取消</button>
          <button class="btn btn-success" :disabled="loading" @click="handleConnect">
            {{ loading ? '连接中...' : '确认连接' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 断开确认 -->
    <div v-if="modal === 'disconnect'" class="modal-overlay" @click.self="modal = null">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>断开连接</h3>
          <button class="btn btn-outline btn-sm" @click="modal = null">✕</button>
        </div>
        <p class="text-sm text-muted mb-2">断开后，正在评测的提交将被标记为 SE。</p>
        <div class="flex gap-1">
          <button class="btn btn-outline" @click="modal = null">取消</button>
          <button class="btn btn-danger" :disabled="loading" @click="handleDisconnect">
            {{ loading ? '断开中...' : '确认断开' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-card {
  background: #fff; border-radius: var(--radius); padding: 24px;
  width: 400px; max-width: 90vw; box-shadow: var(--shadow-md);
}
</style>