<script setup>
import { ref } from 'vue'
import { adminApi } from '../../api/admin'

const title = ref('')
const content = ref('')
const byType = ref('id')   // 'id' | 'username'
const userId = ref(null)
const username = ref('')
const msg = ref(null)
const loading = ref(false)

async function handleSend() {
  msg.value = null
  if (!title.value || !content.value) {
    msg.value = { type: 'error', text: '请填写标题和内容' }
    return
  }
  if (byType.value === 'id' && !userId.value) {
    msg.value = { type: 'error', text: '请填写目标用户 ID' }
    return
  }
  if (byType.value === 'username' && !username.value.trim()) {
    msg.value = { type: 'error', text: '请填写目标用户名' }
    return
  }
  loading.value = true
  try {
    const opts = byType.value === 'id' ? { userId: userId.value } : { username: username.value.trim() }
    const res = await adminApi.sendNotification(title.value, content.value, opts)
    if (res.code === 0) {
      msg.value = { type: 'success', text: res.message }
      title.value = ''
      content.value = ''
      userId.value = null
      username.value = ''
    } else {
      msg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    msg.value = { type: 'error', text: e.message }
  }
  loading.value = false
}
</script>

<template>
  <div>
    <div class="page-header"><h1>发送系统消息</h1></div>

    <div v-if="msg" :class="msg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
      {{ msg.text }}
    </div>

    <div class="card">
      <div class="form-group">
        <label class="form-label">目标用户</label>
        <div class="flex gap-2" style="align-items:center">
          <select v-model="byType" class="form-select" style="max-width:120px">
            <option value="id">按用户 ID</option>
            <option value="username">按用户名</option>
          </select>
          <input v-if="byType === 'id'" v-model.number="userId" class="form-input" style="max-width:180px"
            type="number" placeholder="用户 ID" />
          <input v-else v-model="username" class="form-input" style="max-width:180px"
            placeholder="用户名" />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">标题 <span class="text-muted">(不超过100字符)</span></label>
        <input v-model="title" class="form-input" maxlength="100" placeholder="消息标题" />
      </div>

      <div class="form-group">
        <label class="form-label">内容 <span class="text-muted">(不超过500字符)</span></label>
        <textarea v-model="content" class="form-textarea" rows="8" maxlength="500" placeholder="消息正文..."></textarea>
        <span class="text-sm text-muted">{{ content.length }}/500</span>
      </div>

      <button class="btn btn-primary btn-lg" :disabled="loading" @click="handleSend">
        {{ loading ? '发送中...' : '发送消息' }}
      </button>
    </div>
  </div>
</template>