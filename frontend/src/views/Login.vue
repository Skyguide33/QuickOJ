<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'
import { userApi } from '../api/user'

const router = useRouter()
const auth = useAuthStore()
const notif = useNotificationStore()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMsg.value = '请填写用户名和密码'
    return
  }
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await userApi.login({ username: username.value, password: password.value })
    if (res.code === 0) {
      auth.setAuth(res.data)
      notif.fetchUnreadCount()
      router.push('/')
    } else {
      errorMsg.value = res.message
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="text-center mb-2">登录</h1>
      <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input v-model="username" class="form-input" type="text" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input v-model="password" class="form-input" type="password" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <button class="btn btn-primary btn-lg" style="width:100%" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <p class="text-center text-muted mt-2" style="margin-top:16px">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 120px);
}
.auth-card {
  width: 400px;
  max-width: 100%;
}
</style>
