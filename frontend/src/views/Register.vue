<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api/user'

const router = useRouter()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const loading = ref(false)

async function handleRegister() {
  errorMsg.value = ''
  successMsg.value = ''

  if (!username.value || !password.value) {
    errorMsg.value = '请填写用户名和密码'
    return
  }
  if (username.value.length < 4 || username.value.length > 20) {
    errorMsg.value = '用户名需 4~20 位'
    return
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(username.value)) {
    errorMsg.value = '用户名只能包含字母、数字、下划线，且首字符不能是数字'
    return
  }
  if (password.value.length < 6 || password.value.length > 32) {
    errorMsg.value = '密码需 6~32 位'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    const res = await userApi.register({
      username: username.value,
      password: password.value,
    })
    if (res.code === 0) {
      successMsg.value = '注册成功！即将跳转到登录页...'
      setTimeout(() => router.push('/login'), 1500)
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
      <h1 class="text-center mb-2">注册</h1>
      <div v-if="errorMsg" class="alert alert-error">{{ errorMsg }}</div>
      <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label class="form-label">用户名 <span class="text-muted">(4~20位，字母/数字/下划线，首字不能是数字)</span></label>
          <input v-model="username" class="form-input" type="text" placeholder="字母开头，不含空格和特殊字符" autocomplete="username" />
        </div>
        <div class="form-group">
          <label class="form-label">密码 <span class="text-muted">(6~32位)</span></label>
          <input v-model="password" class="form-input" type="password" placeholder="请输入密码" autocomplete="new-password" />
        </div>
        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input v-model="confirmPassword" class="form-input" type="password" placeholder="请再次输入密码" autocomplete="new-password" />
        </div>
        <button class="btn btn-primary btn-lg" style="width:100%" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      <p class="text-center text-muted mt-2" style="margin-top:16px">
        已有账号？<router-link to="/login">立即登录</router-link>
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
