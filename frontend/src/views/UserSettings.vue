<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { assetUrl } from '../utils/time'
import { userApi } from '../api/user'

const router = useRouter()
const auth = useAuthStore()

// Update profile
const editUsername = ref(auth.user?.username || '')
const editEmail = ref(auth.user?.email || '')
const editMsg = ref(null)
const editLoading = ref(false)

async function handleUpdateProfile() {
  editMsg.value = null
  editLoading.value = true
  try {
    const res = await userApi.update(auth.user.user_id, {
      username: editUsername.value || undefined,
      email: editEmail.value || undefined,
    })
    if (res.code === 0) {
      auth.setUser({ ...auth.user, ...res.data })
      editMsg.value = { type: 'success', text: '更新成功' }
    } else {
      editMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    editMsg.value = { type: 'error', text: e.message }
  }
  editLoading.value = false
}

// Change password
const oldPassword = ref('')
const newPassword = ref('')
const pwdMsg = ref(null)
const pwdLoading = ref(false)

async function handleChangePassword() {
  pwdMsg.value = null
  if (!oldPassword.value || !newPassword.value) {
    pwdMsg.value = { type: 'error', text: '请填写所有密码字段' }
    return
  }
  if (newPassword.value.length < 6) {
    pwdMsg.value = { type: 'error', text: '新密码需 6 位以上' }
    return
  }
  pwdLoading.value = true
  try {
    const res = await userApi.changePassword(auth.user.user_id, {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    if (res.code === 0) {
      auth.setToken(res.data.token)
      pwdMsg.value = { type: 'success', text: '密码修改成功' }
      oldPassword.value = ''
      newPassword.value = ''
    } else {
      pwdMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    pwdMsg.value = { type: 'error', text: e.message }
  }
  pwdLoading.value = false
}

// Upload avatar
const avatarMsg = ref(null)
const avatarLoading = ref(false)

async function handleAvatarUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  avatarMsg.value = null
  avatarLoading.value = true
  try {
    const fd = new FormData()
    fd.append('avatar', file)
    const res = await userApi.uploadAvatar(auth.user.user_id, fd)
    if (res.code === 0) {
      auth.setUser({ ...auth.user, avatar: res.data.avatar })
      avatarMsg.value = { type: 'success', text: '头像更新成功' }
    } else {
      avatarMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    avatarMsg.value = { type: 'error', text: e.message }
  }
  avatarLoading.value = false
}
</script>

<template>
  <div>
    <div class="page-header"><h1>账号设置</h1></div>

    <!-- Profile -->
    <div class="card">
      <h2 class="card-title">基本信息</h2>
      <div v-if="editMsg" :class="editMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
        {{ editMsg.text }}
      </div>
      <div class="form-group">
        <label class="form-label">用户名</label>
        <input v-model="editUsername" class="form-input" style="max-width:320px" />
      </div>
      <div class="form-group">
        <label class="form-label">邮箱</label>
        <input v-model="editEmail" class="form-input" style="max-width:320px" type="email" />
      </div>
      <button class="btn btn-primary" :disabled="editLoading" @click="handleUpdateProfile">
        {{ editLoading ? '保存中...' : '保存修改' }}
      </button>
    </div>

    <!-- Avatar -->
    <div class="card mt-2">
      <h2 class="card-title">头像</h2>
      <div v-if="avatarMsg" :class="avatarMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
        {{ avatarMsg.text }}
      </div>
      <div class="flex gap-2" style="align-items:center">
        <img v-if="auth.user?.avatar" :src="assetUrl(auth.user.avatar)" class="avatar-preview" />
        <div v-else class="avatar-preview avatar-placeholder">{{ auth.user?.username?.[0]?.toUpperCase() }}</div>
        <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="handleAvatarUpload" />
        <span class="text-sm text-muted">支持 jpg/png/gif/webp，不超过 5MB</span>
      </div>
    </div>

    <!-- Change Password -->
    <div class="card mt-2">
      <h2 class="card-title">修改密码</h2>
      <div v-if="pwdMsg" :class="pwdMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
        {{ pwdMsg.text }}
      </div>
      <div class="form-group">
        <label class="form-label">当前密码</label>
        <input v-model="oldPassword" class="form-input" style="max-width:320px" type="password" />
      </div>
      <div class="form-group">
        <label class="form-label">新密码 <span class="text-muted">(6~32位)</span></label>
        <input v-model="newPassword" class="form-input" style="max-width:320px" type="password" />
      </div>
      <button class="btn btn-danger" :disabled="pwdLoading" @click="handleChangePassword">
        {{ pwdLoading ? '修改中...' : '修改密码' }}
      </button>
      <p class="text-sm text-muted mt-1">修改密码后其他设备将被踢下线，需重新登录</p>
    </div>
  </div>
</template>

<style scoped>
.avatar-preview {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-placeholder { font-size: 28px; font-weight: 700; color: var(--primary); }
</style>
