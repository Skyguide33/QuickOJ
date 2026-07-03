<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { formatDate, formatTimeShort } from '../utils/time'
import { assetUrl } from '../utils/time'
import { userApi } from '../api/user'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const profile = ref(null)
const profileError = ref('')
const solvedList = ref([])
const solvedTotal = ref(0)
const uploadedProblems = ref([])
const loading = ref(true)
const uploadedPage = ref(1)
const uploadedTotal = ref(0)
const page = ref(1)
const size = 20

const tab = ref('uploaded')
const isSelf = () => auth.isLoggedIn && auth.user?.user_id === Number(route.params.id)

// ---- Modals ----
const modal = ref(null) // 'avatar' | 'profile' | 'password'
const modalMsg = ref(null)
const modalLoading = ref(false)

function openModal(name) { modal.value = name; modalMsg.value = null }
function closeModal() { modal.value = null; modalMsg.value = null }

// Profile form
const editUsername = ref('')
const editEmail = ref('')
function openProfileModal() {
  editUsername.value = auth.user?.username || ''
  editEmail.value = auth.user?.email || ''
  openModal('profile')
}

async function handleUpdateProfile() {
  modalMsg.value = null; modalLoading.value = true
  try {
    const res = await userApi.update(auth.user.user_id, {
      username: editUsername.value || undefined,
      email: editEmail.value || undefined,
    })
    if (res.code === 0) {
      auth.setUser({ ...auth.user, ...res.data })
      modalMsg.value = { type: 'success', text: '更新成功' }
      setTimeout(closeModal, 800)
    } else {
      modalMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) { modalMsg.value = { type: 'error', text: e.message } }
  modalLoading.value = false
}

// Password form
const oldPwd = ref('')
const newPwd = ref('')
function openPasswordModal() {
  oldPwd.value = ''; newPwd.value = ''
  openModal('password')
}

async function handleChangePassword() {
  modalMsg.value = null
  if (!oldPwd.value || !newPwd.value) { modalMsg.value = { type: 'error', text: '请填写所有字段' }; return }
  if (newPwd.value.length < 6) { modalMsg.value = { type: 'error', text: '新密码需至少 6 位' }; return }
  modalLoading.value = true
  try {
    const res = await userApi.changePassword(auth.user.user_id, {
      old_password: oldPwd.value, new_password: newPwd.value,
    })
    if (res.code === 0) {
      auth.setToken(res.data.token)
      modalMsg.value = { type: 'success', text: '密码修改成功' }
      setTimeout(closeModal, 800)
    } else {
      modalMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) { modalMsg.value = { type: 'error', text: e.message } }
  modalLoading.value = false
}

// Avatar upload
const avatarFile = ref(null)
const avatarPreview = ref('')
const avatarUploading = ref(false)

function handleAvatarFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    modalMsg.value = { type: 'error', text: '文件过大，不超过 5MB' }
    return
  }
  avatarFile.value = file
  modalMsg.value = null
  // 本地预览
  const reader = new FileReader()
  reader.onload = () => { avatarPreview.value = reader.result }
  reader.readAsDataURL(file)
}

async function confirmAvatar() {
  if (!avatarFile.value) return
  avatarUploading.value = true; modalMsg.value = null
  try {
    const fd = new FormData(); fd.append('avatar', avatarFile.value)
    const res = await userApi.uploadAvatar(auth.user.user_id, fd)
    if (res.code === 0) {
      auth.setUser({ ...auth.user, avatar: res.data.avatar })
      if (profile.value) profile.value.avatar = res.data.avatar
      closeModal()
    } else {
      modalMsg.value = { type: 'error', text: res.message }
    }
  } catch (e) { modalMsg.value = { type: 'error', text: e.message } }
  avatarUploading.value = false
}

function openAvatarModal() {
  avatarFile.value = null
  avatarPreview.value = ''
  modalMsg.value = null
  modal.value = 'avatar'
}

async function fetchProfile() {
  loading.value = true
  profileError.value = ''

  const identifier = route.params.id
  const isName = !/^\d+$/.test(identifier)  // 非纯数字 → 用户名

  try {
    const res = await userApi.getPublicProfile(identifier)
    if (res.code === 0) {
      profile.value = res.data
      document.title = `${res.data.username} 的主页 - QuickOJ`
      // 用户名访问 → 替换 URL 为 /user/{user_id}
      if (isName) {
        router.replace({ params: { id: String(res.data.user_id) } })
      }
      fetchSolved()
      fetchUploadedProblems()
    } else {
      profileError.value = res.message || '加载失败'
    }
  } catch (e) {
    profileError.value = e.message || '网络错误'
  }
  loading.value = false
}

async function fetchSolved() {
  try {
    const res = await userApi.getSolvedProblems(route.params.id, { page: page.value, size })
    if (res.code === 0) { solvedList.value = res.data.list; solvedTotal.value = res.data.pagination.total }
  } catch { /* ignore */ }
}

async function fetchUploadedProblems() {
  try {
    const res = await userApi.getUserProblems(route.params.id, { page: uploadedPage.value, size })
    if (res.code === 0) {
      uploadedProblems.value = res.data.list
      uploadedTotal.value = res.data.pagination.total
    }
  } catch { /* ignore */ }
}

function onUploadedPageChange(p) { uploadedPage.value = p; fetchUploadedProblems() }
function onPageChange(p) { page.value = p; fetchSolved() }

onMounted(() => { fetchProfile() })
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>
  <div v-else-if="!profile" class="card empty-state">
    <p v-if="profileError" class="alert alert-error">{{ profileError }}</p>
    <p v-else>用户不存在</p>
  </div>

  <div v-else>
    <!-- Profile Card -->
    <div class="card">
      <div class="flex gap-2" style="align-items:center">
        <div class="avatar-lg">
          <img v-if="profile.avatar" :src="assetUrl(profile.avatar)" alt="avatar" />
          <span v-else class="avatar-placeholder">{{ profile.username?.[0]?.toUpperCase() }}</span>
        </div>
        <div>
          <h1 style="font-size:24px">{{ profile.username }}</h1>
          <div class="mt-1 flex gap-1">
            <span class="badge" :class="profile.role === 'root' ? 'badge-danger' : profile.role === 'admin' ? 'badge-warning' : 'badge-info'">
              {{ profile.role === 'root' ? '站长' : profile.role === 'admin' ? '管理员' : '用户' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Stats row + action buttons -->
      <div class="stats-row mt-2">
        <div class="stat-item">
          <span class="stat-value">{{ profile.solved_problems || 0 }}</span>
          <span class="stat-label">解题数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ profile.total_submissions || 0 }}</span>
          <span class="stat-label">总提交</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ formatDate(profile.registered_at) }}</span>
          <span class="stat-label">注册时间</span>
        </div>
        <div class="stat-actions">
          <router-link :to="`/submissions?username=${profile.username}`" class="btn btn-outline btn-sm">提交记录</router-link>
          <template v-if="isSelf()">
            <button class="btn btn-outline btn-sm" @click="openAvatarModal">修改头像</button>
            <button class="btn btn-outline btn-sm" @click="openProfileModal">修改个人资料</button>
            <button class="btn btn-outline btn-sm" @click="openPasswordModal">修改密码</button>
          </template>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="card mt-2" style="padding:0">
      <div class="tabs">
        <button :class="{ active: tab === 'uploaded' }" @click="tab = 'uploaded'">发布的题目 ({{ uploadedTotal }})</button>
        <button :class="{ active: tab === 'solved' }" @click="tab = 'solved'">通过的题目 ({{ solvedTotal }})</button>
      </div>
    </div>

    <!-- 通过的题目 -->
    <div v-if="tab === 'solved'" class="card">
      <div class="flex-between mb-2">
        <h3 class="card-title" style="margin:0">通过的题目</h3>
        <router-link :to="`/submissions?username=${profile.username}`" class="btn btn-outline btn-sm">提交记录 →</router-link>
      </div>
      <!-- 最近通过 -->
      <div v-if="profile.recent_accepted?.length" class="recent-list mb-2">
        <div class="mb-1">
          <h3 class="text-sm text-muted">最近通过</h3>
        </div>
        <div v-for="item in profile.recent_accepted" :key="item.problem_id" class="recent-item">
          <router-link :to="`/problems/${item.problem_number || 'p' + item.problem_id}`">
            {{ item.problem_number || '#' + item.problem_id }} {{ item.problem_name }}
          </router-link>
          <span class="text-sm text-muted">{{ formatTimeShort(item.first_accepted_at) }}</span>
        </div>
      </div>
      <!-- 全部通过 -->
      <div v-if="solvedList.length === 0" class="text-muted text-sm">暂无</div>
      <div v-else>
        <h3 class="text-sm text-muted mb-1">已通过的题目</h3>
        <div class="solved-inline">
          <router-link
            v-for="item in solvedList" :key="item.problem_id"
            :to="`/problems/${item.problem_number || 'p' + item.problem_id}`"
            class="solved-link"
          >{{ item.problem_number || '#' + item.problem_id }}</router-link>
        </div>
      </div>
      <Pagination :page="page" :size="size" :total="solvedTotal" @change="onPageChange" />
    </div>

    <!-- 发布的题目 -->
    <div v-if="tab === 'uploaded'" class="card">
      <div v-if="uploadedProblems.length === 0" class="text-muted text-sm">暂无</div>
      <div v-else class="uploaded-list">
        <div v-for="p in uploadedProblems" :key="p.problem_id" class="uploaded-item">
          <router-link :to="`/problems/${p.problem_number || 'p' + p.problem_id}`">
            {{ p.problem_number || '#' + p.problem_id }} {{ p.problem_name }}
          </router-link>
          <span v-if="isSelf() || auth.isAdmin" class="badge"
            :class="p.problem_status === 'approved' ? 'badge-success' : p.problem_status === 'pending_new' || p.problem_status === 'pending_modify' ? 'badge-warning' : 'badge-info'"
            style="margin-left:8px;font-size:11px">{{
              {approved:'公开',pending_new:'待审核',pending_modify:'重新审核',rejected:'不通过',frozen:'冻结',archived:'归档'}[p.problem_status] || p.problem_status
            }}</span>
          <span class="text-sm text-muted" style="margin-left:auto">{{ formatDate(p.created_at) }}</span>
        </div>
      </div>
      <Pagination :page="uploadedPage" :size="size" :total="uploadedTotal" @change="onUploadedPageChange" />
    </div>

    <!-- ============== Modals ============== -->
    <div v-if="modal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>{{ modal === 'avatar' ? '修改头像' : modal === 'profile' ? '修改个人资料' : '修改密码' }}</h3>
          <button class="btn btn-outline btn-sm" @click="closeModal">✕</button>
        </div>

        <div v-if="modalMsg" :class="modalMsg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
          {{ modalMsg.text }}
        </div>

        <!-- Avatar -->
        <template v-if="modal === 'avatar'">
          <div class="avatar-modal-body">
            <div class="avatar-preview-box">
              <img v-if="avatarPreview" :src="avatarPreview" class="avatar-preview-lg" />
              <img v-else-if="auth.user?.avatar" :src="assetUrl(auth.user.avatar)" class="avatar-preview-lg" />
              <div v-else class="avatar-preview-lg avatar-placeholder-lg">{{ auth.user?.username?.[0]?.toUpperCase() }}</div>
              <div v-if="avatarUploading" class="avatar-spinner">⟳</div>
            </div>
            <label class="btn btn-outline btn-sm avatar-file-btn">
              选择图片
              <input type="file" accept="image/jpeg,image/png,image/gif,image/webp"
                style="display:none" @change="handleAvatarFile" />
            </label>
            <p class="text-sm text-muted mt-1">支持 jpg/png/gif/webp，不超过 5MB</p>
          </div>
          <div class="flex gap-1 mt-2" style="justify-content:flex-end">
            <button class="btn btn-outline" @click="closeModal">取消</button>
            <button class="btn btn-primary" :disabled="!avatarFile || avatarUploading" @click="confirmAvatar">
              {{ avatarUploading ? '上传中...' : '确认更新' }}
            </button>
          </div>
        </template>

        <!-- Profile -->
        <template v-if="modal === 'profile'">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input v-model="editUsername" class="form-input" placeholder="4~20 位" />
          </div>
          <div class="form-group">
            <label class="form-label">邮箱</label>
            <input v-model="editEmail" class="form-input" type="email" placeholder="可选" />
          </div>
          <button class="btn btn-primary" :disabled="modalLoading" @click="handleUpdateProfile">
            {{ modalLoading ? '保存中...' : '保存' }}
          </button>
        </template>

        <!-- Password -->
        <template v-if="modal === 'password'">
          <div class="form-group">
            <label class="form-label">当前密码</label>
            <input v-model="oldPwd" class="form-input" type="password" placeholder="输入当前密码" />
          </div>
          <div class="form-group">
            <label class="form-label">新密码</label>
            <input v-model="newPwd" class="form-input" type="password" placeholder="6~32 位" />
          </div>
          <button class="btn btn-danger" :disabled="modalLoading" @click="handleChangePassword">
            {{ modalLoading ? '修改中...' : '修改密码' }}
          </button>
          <p class="text-sm text-muted mt-1">修改后其他设备将需要重新登录</p>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.avatar-lg {
  width: 80px; height: 80px; border-radius: 50%; overflow: hidden;
  background: var(--primary-light); display: flex; align-items: center; justify-content: center;
}
.avatar-lg img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder { font-size: 32px; font-weight: 700; color: var(--primary); }

.stats-row { display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--primary); }
.stat-label { font-size: 13px; color: var(--gray-500); }
.stat-actions { margin-left: auto; display: flex; gap: 8px; }

.recent-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--gray-100); }
.solved-inline { display: flex; flex-wrap: wrap; gap: 10px 16px; }
.tabs {
  display: flex; border-bottom: 2px solid var(--gray-200);
}
.tabs button {
  padding: 12px 20px; border: none; background: none;
  font-size: 14px; font-weight: 500; cursor: pointer;
  color: var(--gray-600); border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all .15s;
}
.tabs button:hover { color: var(--primary); }
.tabs button.active { color: var(--primary); border-bottom-color: var(--primary); }
.solved-link { color: var(--primary); font-weight: 600; font-size: 16px; }
.solved-link:hover { color: var(--primary-hover); }
.uploaded-item {
  display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--gray-100);
}

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal-card {
  background: #fff; border-radius: var(--radius); padding: 24px;
  width: 420px; max-width: 90vw; box-shadow: var(--shadow-md);
}
.avatar-preview { width: 56px; height: 56px; border-radius: 50%; object-fit: cover; background: var(--primary-light); display: flex; align-items: center; justify-content: center; }
.avatar-placeholder-sm { font-size: 22px; font-weight: 700; color: var(--primary); }

/* Avatar modal */
.avatar-modal-body { text-align: center; }
.avatar-preview-box { position: relative; display: inline-block; margin-bottom: 12px; }
.avatar-preview-lg {
  width: 160px; height: 160px; border-radius: 50%; object-fit: cover;
  border: 4px solid var(--gray-200); background: var(--primary-light);
}
.avatar-placeholder-lg {
  display: flex; align-items: center; justify-content: center;
  font-size: 64px; font-weight: 700; color: var(--primary);
}
.avatar-spinner {
  position: absolute; inset: 0; border-radius: 50%;
  background: rgba(255,255,255,.7); display: flex; align-items: center; justify-content: center;
  font-size: 40px; color: var(--primary);
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.avatar-file-btn { cursor: pointer; display: inline-block; }
</style>