<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { adminApi } from '../../api/admin'
import Pagination from '../../components/Pagination.vue'

const auth = useAuthStore()

const ROLE_LEVEL = { root: 1, admin: 2, user: 3 }

function canManage(targetUser) {
  // 不能操作自己
  if (targetUser.user_id === auth.user?.user_id) return false
  // 只能操作权限低于自己的用户（数字越大权限越低）
  const myLevel = ROLE_LEVEL[auth.role] || 99
  const targetLevel = ROLE_LEVEL[targetUser.role] || 99
  return myLevel < targetLevel
}

const users = ref([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const size = 20

const filterRole = ref('')
const filterStatus = ref('')
const filterKeyword = ref('')
const msg = ref(null)

async function fetchUsers() {
  loading.value = true
  try {
    const params = { page: page.value, size }
    if (filterRole.value) params.role = filterRole.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterKeyword.value) params.keyword = filterKeyword.value
    const res = await adminApi.getUsers(params)
    if (res.code === 0) {
      users.value = res.data.list
      total.value = res.data.pagination.total
    }
  } catch { /* ignore */ }
  loading.value = false
}

async function changeRole(userId, newRole) {
  if (!confirm(`确定将用户 #${userId} 的角色改为 ${newRole}？`)) return
  msg.value = null
  try {
    const res = await adminApi.changeUserRole(userId, newRole)
    if (res.code === 0) {
      msg.value = { type: 'success', text: res.message }
      fetchUsers()
    } else {
      msg.value = { type: 'error', text: res.message }
    }
  } catch (e) { msg.value = { type: 'error', text: e.message } }
}

async function changeStatus(userId, newStatus, reason) {
  const action = newStatus === 'banned' ? '封禁' : '解封'
  const r = reason || (newStatus === 'banned' ? prompt('请输入封禁原因（可选）') : '')
  if (!confirm(`确定${action}用户 #${userId}？`)) return
  msg.value = null
  try {
    const res = await adminApi.changeUserStatus(userId, newStatus, r)
    if (res.code === 0) {
      msg.value = { type: 'success', text: res.message }
      fetchUsers()
    } else {
      msg.value = { type: 'error', text: res.message }
    }
  } catch (e) { msg.value = { type: 'error', text: e.message } }
}

function onSearch() { page.value = 1; fetchUsers() }
function onPageChange(p) { page.value = p; fetchUsers() }

onMounted(fetchUsers)
</script>

<template>
  <div>
    <div class="page-header"><h1>用户管理</h1></div>

    <div v-if="msg" :class="msg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
      {{ msg.text }}
    </div>

    <div class="card" style="padding:16px">
      <div class="flex flex-wrap gap-1">
        <input v-model="filterKeyword" class="form-input" style="max-width:160px" placeholder="搜索用户名" @keyup.enter="onSearch" />
        <select v-model="filterRole" class="form-select" style="max-width:120px" @change="onSearch">
          <option value="">全部角色</option>
          <option value="root">站长</option>
          <option value="admin">管理员</option>
          <option value="user">用户</option>
        </select>
        <select v-model="filterStatus" class="form-select" style="max-width:120px" @change="onSearch">
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="banned">已封禁</option>
        </select>
        <button class="btn btn-primary btn-sm" @click="onSearch">搜索</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else class="card table-container" style="padding:0">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>角色</th>
            <th>状态</th>
            <th>解题数</th>
            <th>总提交</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.user_id">
            <td>{{ u.user_id }}</td>
            <td>{{ u.username }}</td>
            <td>
              <span class="badge" :class="u.role === 'root' ? 'badge-danger' : u.role === 'admin' ? 'badge-warning' : 'badge-info'">
                {{ u.role }}
              </span>
            </td>
            <td>
              <span class="badge" :class="u.status === 'active' ? 'badge-success' : 'badge-danger'">
                {{ u.status === 'active' ? '正常' : '已封禁' }}
              </span>
            </td>
            <td>{{ u.solved_problems }}</td>
            <td>{{ u.total_submissions }}</td>
            <td class="text-sm text-muted">{{ u.registered_at?.slice(0, 10) }}</td>
            <td>
              <div class="flex gap-1">
                <!-- 角色变更：仅站长可操作，站长唯一不可转让 -->
                <template v-if="auth.isRoot && u.user_id !== auth.user?.user_id">
                  <button v-if="u.role !== 'admin'" class="btn btn-outline btn-sm"
                    @click="changeRole(u.user_id, 'admin')">设为管理员</button>
                  <button v-if="u.role === 'admin'" class="btn btn-outline btn-sm"
                    @click="changeRole(u.user_id, 'user')">降为普通用户</button>
                </template>
                <!-- 封禁/解封：仅能操作权限低于自己的用户 -->
                <template v-if="canManage(u)">
                  <button v-if="u.status === 'active'" class="btn btn-outline btn-sm" style="color:var(--danger)"
                    @click="changeStatus(u.user_id, 'banned')">封禁</button>
                  <button v-else class="btn btn-outline btn-sm" style="color:var(--success)"
                    @click="changeStatus(u.user_id, 'active')">解封</button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination :page="page" :size="size" :total="total" @change="onPageChange" />
  </div>
</template>
