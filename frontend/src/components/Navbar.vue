<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { assetUrl } from '../utils/time'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'

const router = useRouter()
const auth = useAuthStore()
const notif = useNotificationStore()

const menuOpen = ref(false)
const logoutModal = ref(false)

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function goReview() {
  closeMenu()
  router.push('/problems?review_mode=true&sort_by=created_at&sort_order=desc')
}

function confirmLogout() {
  logoutModal.value = false
  auth.logout()
  notif.setUnreadCount(0)
  closeMenu()
  router.push('/')
}

function handleLogout() {
  closeMenu()
  logoutModal.value = true
}

watch(() => auth.isLoggedIn, (val) => {
  if (val) notif.fetchUnreadCount()
})

onMounted(() => {
  if (auth.isLoggedIn) notif.fetchUnreadCount()
})
</script>

<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="navbar-brand" @click="closeMenu">
        <img src="/favicon.svg" width="28" height="28" style="vertical-align:middle;margin-right:6px" alt="" />
        QuickOJ
      </router-link>

      <!-- Hamburger -->
      <button class="hamburger" @click="toggleMenu" aria-label="菜单">
        <span :class="{ open: menuOpen }"></span>
      </button>

      <!-- Nav links -->
      <div class="navbar-links" :class="{ open: menuOpen }">
        <router-link to="/problems" @click="closeMenu">题库</router-link>
        <router-link v-if="auth.isLoggedIn" to="/submissions" @click="closeMenu">提交记录</router-link>
        <router-link to="/ranking" @click="closeMenu">排行榜</router-link>

        <!-- Admin dropdown -->
        <div v-if="auth.isAdmin" class="nav-dropdown">
          <button class="nav-dropdown-btn">管理 ▾</button>
          <div class="nav-dropdown-menu">
            <router-link v-if="auth.isRoot" to="/admin/users" @click="closeMenu">用户管理</router-link>
            <a href="#" @click.prevent="goReview">题目审核</a>
            <router-link to="/admin/notifications" @click="closeMenu">发送通知</router-link>
            <router-link to="/admin/judge" @click="closeMenu">评测机</router-link>
          </div>
        </div>

        <div class="navbar-spacer"></div>

        <!-- Not logged in -->
        <template v-if="!auth.isLoggedIn">
          <router-link to="/login" class="btn btn-outline btn-sm" @click="closeMenu">登录</router-link>
          <router-link to="/register" class="btn btn-primary btn-sm" @click="closeMenu">注册</router-link>
        </template>

        <!-- Logged in -->
        <template v-else>
          <router-link to="/notifications" class="nav-icon-link" @click="closeMenu" title="通知">
            🔔
            <span v-if="notif.unreadCount > 0" class="nav-badge">{{ notif.unreadCount > 99 ? '99+' : notif.unreadCount }}</span>
          </router-link>
          <div class="nav-dropdown">
            <button class="nav-avatar-btn" :title="auth.user?.username">
              <img v-if="auth.user?.avatar" :src="assetUrl(auth.user.avatar)" class="nav-avatar-img" />
              <span v-else class="nav-avatar-placeholder">{{ auth.user?.username?.[0]?.toUpperCase() }}</span>
            </button>
            <div class="nav-dropdown-menu">
              <router-link :to="`/user/${auth.user?.user_id}`" @click="closeMenu">个人主页</router-link>
              <a href="#" @click.prevent="handleLogout">退出登录</a>
            </div>
          </div>
        </template>
      </div>
    </div>
  </nav>

  <!-- 退出确认弹窗 -->
  <div v-if="logoutModal" class="modal-overlay" @click.self="logoutModal = false">
    <div class="modal-card">
      <div class="flex-between mb-2">
        <h3>退出登录</h3>
        <button class="btn btn-outline btn-sm" @click="logoutModal = false">✕</button>
      </div>
      <p class="text-sm text-muted mb-2">确定要退出登录吗？</p>
      <div class="flex gap-1">
        <button class="btn btn-outline" @click="logoutModal = false">取消</button>
        <button class="btn btn-danger" @click="confirmLogout">确认退出</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.navbar {
  background: #fff;
  border-bottom: 1px solid var(--gray-200);
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
}
.navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
  display: flex;
  align-items: center;
  height: 100%;
}
.navbar-brand {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
  margin-right: 24px;
}
.navbar-brand:hover { color: var(--primary-hover); }

/* Hamburger */
.hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  margin-left: auto;
}
.hamburger span,
.hamburger span::before,
.hamburger span::after {
  display: block;
  width: 24px;
  height: 2px;
  background: var(--gray-700);
  transition: .2s;
}
.hamburger span { position: relative; }
.hamburger span::before { content: ''; position: absolute; top: -7px; }
.hamburger span::after  { content: ''; position: absolute; top: 7px; }
.hamburger span.open { background: transparent; }
.hamburger span.open::before { top: 0; transform: rotate(45deg); }
.hamburger span.open::after  { top: 0; transform: rotate(-45deg); }

.navbar-links {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.navbar-links > a {
  padding: 6px 12px;
  font-size: 14px;
  color: var(--gray-700);
  border-radius: var(--radius);
}
.navbar-links > a:hover { background: var(--gray-100); }
.navbar-links > a.router-link-active { color: var(--primary); font-weight: 600; }
.navbar-spacer { flex: 1; }

.nav-icon-link {
  position: relative;
  font-size: 18px;
  padding: 6px 8px;
}
.nav-badge {
  position: absolute;
  top: 0;
  right: -2px;
  background: var(--danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 0 4px;
  border-radius: 10px;
  min-width: 16px;
  text-align: center;
  line-height: 16px;
}

.nav-dropdown { position: relative; }
.nav-dropdown-btn {
  background: none;
  border: none;
  font-size: 14px;
  font-family: inherit;
  color: var(--gray-700);
  cursor: pointer;
  padding: 6px 8px;
  border-radius: var(--radius);
}
.nav-dropdown-btn:hover { background: var(--gray-100); }

.nav-avatar-btn {
  background: none; border: none; cursor: pointer; padding: 2px;
  border-radius: 50%; transition: box-shadow .15s;
}
.nav-avatar-btn:hover { box-shadow: 0 0 0 3px rgba(79,70,229,.25); }
.nav-avatar-img {
  width: 34px; height: 34px; border-radius: 50%; object-fit: cover;
  display: block;
}
.nav-avatar-placeholder {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--primary-light); color: var(--primary);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700;
}

.nav-dropdown-menu {
  display: none;
  position: absolute;
  top: 100%;
  right: 0;
  background: #fff;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  min-width: 140px;
  padding: 4px;
}
.nav-dropdown:hover .nav-dropdown-menu { display: block; }
.nav-dropdown-menu a {
  display: block;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--gray-700);
  border-radius: 4px;
}
.nav-dropdown-menu a:hover { background: var(--gray-100); }

@media (max-width: 768px) {
  .hamburger { display: block; }
  .navbar-links {
    display: none;
    position: absolute;
    top: 56px;
    left: 0;
    right: 0;
    background: #fff;
    border-bottom: 1px solid var(--gray-200);
    flex-direction: column;
    padding: 12px 16px;
    gap: 4px;
    align-items: stretch;
  }
  .navbar-links.open { display: flex; }
  .nav-dropdown-menu { position: static; box-shadow: none; border: none; padding-left: 16px; }
}
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal-card { background: #fff; border-radius: var(--radius); padding: 24px; width: 360px; max-width: 90vw; box-shadow: var(--shadow-md); }
</style>
