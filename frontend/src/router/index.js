import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const TITLE_SUFFIX = 'QuickOJ'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { title: `首页 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true, title: `登录 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true, title: `注册 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/problems',
    name: 'ProblemList',
    component: () => import('../views/ProblemList.vue'),
    meta: { title: `题库 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/problems/create',
    name: 'CreateProblem',
    component: () => import('../views/CreateProblem.vue'),
    meta: { requiresAuth: true, title: `上传题目 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/problems/:identifier',
    name: 'ProblemDetail',
    component: () => import('../views/ProblemDetail.vue'),
    meta: { title: null }, // 组件内动态设置
  },
  {
    path: '/problems/:identifier/edit',
    name: 'EditProblem',
    component: () => import('../views/EditProblem.vue'),
    meta: { requiresAuth: true, title: `编辑题目 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/submissions',
    name: 'SubmissionList',
    component: () => import('../views/SubmissionList.vue'),
    meta: { requiresAuth: true, title: `提交记录 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/submissions/:id',
    name: 'SubmissionDetail',
    component: () => import('../views/SubmissionDetail.vue'),
    meta: { requiresAuth: true, title: null }, // 组件内动态设置
  },
  {
    path: '/ranking',
    name: 'Ranking',
    component: () => import('../views/Ranking.vue'),
    meta: { title: `排行榜 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/user/:id',
    name: 'UserProfile',
    component: () => import('../views/UserProfile.vue'),
    meta: { title: null }, // 组件内动态设置
  },
  {
    path: '/notifications',
    name: 'NotificationList',
    component: () => import('../views/NotificationList.vue'),
    meta: { requiresAuth: true, title: `消息通知 - ${TITLE_SUFFIX}` },
  },
  // Admin routes
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/admin/UserManagement.vue'),
    meta: { requiresAuth: true, minRole: 'root', title: `用户管理 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/admin/notifications',
    name: 'AdminSendNotification',
    component: () => import('../views/admin/SendNotification.vue'),
    meta: { requiresAuth: true, minRole: 'admin', title: `发送通知 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/admin/judge',
    name: 'JudgeManagement',
    component: () => import('../views/admin/JudgeManagement.vue'),
    meta: { requiresAuth: true, minRole: 'admin', title: `评测机管理 - ${TITLE_SUFFIX}` },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { title: `404 页面未找到 - ${TITLE_SUFFIX}` },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const ROLE_LEVEL = { root: 1, admin: 2, user: 3, guest: 99 }

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  // 游客路由（登录/注册），已登录则跳转首页
  if (to.meta.guest && auth.isLoggedIn) {
    return next('/')
  }

  // 需要登录
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return next('/login')
  }

  // 需要最低角色
  if (to.meta.minRole) {
    const userLevel = ROLE_LEVEL[auth.role] || 99
    const requiredLevel = ROLE_LEVEL[to.meta.minRole] || 99
    if (userLevel > requiredLevel) {
      return next('/')
    }
  }

  next()
})

// 全局后置守卫：静态标题在此设置，动态标题（null）由组件自行更新
router.afterEach((to) => {
  if (to.meta.title) {
    document.title = to.meta.title
  } else {
    document.title = TITLE_SUFFIX // 动态页面加载中的默认标题
  }
})

export default router
