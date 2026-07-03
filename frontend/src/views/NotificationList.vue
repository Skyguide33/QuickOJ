<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../stores/notification'
import { formatTimeShort } from '../utils/time'
import { notificationsApi } from '../api/notifications'
import Pagination from '../components/Pagination.vue'

const notifStore = useNotificationStore()
const router = useRouter()

const notifications = ref([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const size = 20
const isRead = ref(null)
const confirmDelete = ref(false)
const msg = ref(null)

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, size }
    if (isRead.value !== null) params.is_read = isRead.value
    const res = await notificationsApi.getList(params)
    if (res.code === 0) {
      notifications.value = res.data.list
      total.value = res.data.pagination.total
    }
  } catch { /* ignore */ }
  loading.value = false
}

async function markRead(notificationId) {
  try {
    const res = await notificationsApi.markRead(notificationId)
    if (res.code === 0) {
      const n = notifications.value.find(x => x.notification_id === notificationId)
      if (n) { n.is_read = true; notifStore.decrementUnread() }
    }
  } catch { /* ignore */ }
}

async function markAllRead() {
  try {
    const res = await notificationsApi.markAllRead()
    if (res.code === 0) {
      notifications.value.forEach(n => n.is_read = true)
      notifStore.setUnreadCount(0)
      msg.value = { type: 'success', text: '已全部标记为已读' }
    }
  } catch { /* ignore */ }
}

async function deleteAll() {
  confirmDelete.value = false
  try {
    for (const n of notifications.value) {
      await notificationsApi.delete(n.notification_id)
    }
    notifStore.setUnreadCount(0)
    fetchData()
  } catch { /* ignore */ }
}

async function deleteNotification(notificationId) {
  try {
    const res = await notificationsApi.delete(notificationId)
    if (res.code === 0) {
      const n = notifications.value.find(x => x.notification_id === notificationId)
      if (n && !n.is_read) notifStore.decrementUnread()
      notifications.value = notifications.value.filter(x => x.notification_id !== notificationId)
    }
  } catch { /* ignore */ }
}

function onFilterChange() {
  page.value = 1
  fetchData()
}

function onPageChange(p) { page.value = p; fetchData() }

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="page-header">
      <h1>消息通知</h1>
      <div class="flex gap-1">
        <button v-if="notifStore.unreadCount > 0" class="btn btn-outline btn-sm" @click="markAllRead">
          全部标记为已读
        </button>
        <button v-if="total > 0" class="btn btn-outline btn-sm" style="color:var(--danger)" @click="confirmDelete = true">
          全部删除
        </button>
      </div>
    </div>

    <div v-if="msg" class="alert alert-success">{{ msg.text }}</div>

    <div class="flex gap-1 mb-2">
      <button class="btn btn-sm" :class="isRead === null ? 'btn-primary' : 'btn-outline'"
        @click="isRead = null; onFilterChange()">全部</button>
      <button class="btn btn-sm" :class="isRead === 0 ? 'btn-primary' : 'btn-outline'"
        @click="isRead = 0; onFilterChange()">未读</button>
      <button class="btn btn-sm" :class="isRead === 1 ? 'btn-primary' : 'btn-outline'"
        @click="isRead = 1; onFilterChange()">已读</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="notifications.length === 0" class="card empty-state">
      <p>暂无消息</p>
    </div>

    <div v-else>
      <div v-for="n in notifications" :key="n.notification_id" class="card notification-item" style="padding:16px">
        <div class="flex-between">
          <div style="flex:1">
            <div class="flex gap-1" style="align-items:center">
              <span v-if="!n.is_read" class="unread-dot"></span>
              <strong :style="{ fontWeight: n.is_read ? '400' : '600' }">{{ n.title }}</strong>
            </div>
            <p class="text-sm text-muted mt-1">{{ n.content }}</p>
            <p class="text-sm text-muted">{{ formatTimeShort(n.created_at) }}</p>
          </div>
          <div class="flex gap-1">
            <button v-if="!n.is_read" class="btn btn-outline btn-sm" @click="markRead(n.notification_id)">
              标记已读
            </button>
            <button class="btn btn-outline btn-sm" style="color:var(--danger)" @click="deleteNotification(n.notification_id)">
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <Pagination :page="page" :size="size" :total="total" @change="onPageChange" />

    <!-- 全部删除确认弹窗 -->
    <div v-if="confirmDelete" class="modal-overlay" @click.self="confirmDelete = false">
      <div class="modal-card">
        <div class="flex-between mb-2">
          <h3>全部删除</h3>
          <button class="btn btn-outline btn-sm" @click="confirmDelete = false">✕</button>
        </div>
        <p class="text-sm text-muted mb-2">确定要删除当前页所有消息吗？此操作不可撤销。</p>
        <div class="flex gap-1">
          <button class="btn btn-outline" @click="confirmDelete = false">取消</button>
          <button class="btn btn-danger" @click="deleteAll">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notification-item { transition: background .15s; }
.notification-item:hover { background: var(--gray-50); }
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  display: inline-block;
}
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal-card { background: #fff; border-radius: var(--radius); padding: 24px; width: 380px; max-width: 90vw; box-shadow: var(--shadow-md); }
</style>
