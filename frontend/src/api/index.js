import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { CONFIG } from '../config'

const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const api = axios.create({
  baseURL: BASE || '/api',
  timeout: 30000,
})

// ============================================================
// 页面刷新防抖 —— 冷却期内的刷新不发送网络请求，仅吃缓存
// 每 3 秒内的多次刷新合并为一次有效加载
// ============================================================
const { REFRESH_COOLDOWN_MS: COOLDOWN_MS, REFRESH_COOLDOWN_KEY: COOLDOWN_KEY } = CONFIG
const CACHE_STORAGE_KEY = 'qoj_api_cache'

function getCooldownRemaining() {
  const last = sessionStorage.getItem(COOLDOWN_KEY)
  if (!last) return 0
  const elapsed = Date.now() - Number(last)
  return Math.max(0, COOLDOWN_MS - elapsed)
}

// ============================================================
// 页面加载：冷却期内保留缓存，冷却期外清空（与题库等页面一致）
// ============================================================
const inCooldown = getCooldownRemaining() > 0
if (inCooldown) {
  sessionStorage.setItem(COOLDOWN_KEY, Number(sessionStorage.getItem(COOLDOWN_KEY)))
} else {
  sessionStorage.removeItem(CACHE_STORAGE_KEY)
  sessionStorage.setItem(COOLDOWN_KEY, Date.now())
}

// ============================================================
// 请求级缓存（内存 + sessionStorage）
// ============================================================
const CACHE_TTL = CONFIG.REQUEST_CACHE_TTL
const cache = new Map()

// 从 sessionStorage 恢复缓存
try {
  const stored = sessionStorage.getItem(CACHE_STORAGE_KEY)
  if (stored) {
    const entries = JSON.parse(stored)
    for (const [key, entry] of entries) {
      if (Date.now() - entry.time < CACHE_TTL) {
        cache.set(key, entry)
      }
    }
  }
} catch { /* ignore */ }

function persistCache() {
  try {
    let entries = Array.from(cache.entries())
    // 按时间排序，新的靠后
    entries.sort((a, b) => a[1].time - b[1].time)
    // 尝试写入，若超 sessionStorage 限额则逐步淘汰最旧条目
    while (entries.length > 0) {
      try {
        sessionStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(entries))
        break
      } catch {
        entries.shift()  // 淘汰最旧的一条，重试
      }
    }
  } catch { /* ignore */ }
}

function cacheKey(config) {
  const { method, url, params } = config
  const p = params ? JSON.stringify(params, Object.keys(params).sort()) : ''
  return `${method}:${url}:${p}`
}

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const auth = useAuthStore()
    if (auth.token) {
      config.headers.Authorization = `Bearer ${auth.token}`
    }

    // GET 请求：优先走缓存（命中则零网络请求）
    if (config.method === 'get' && !config._skipCache) {
      const key = cacheKey(config)
      const entry = cache.get(key)
      if (entry && Date.now() - entry.time < CACHE_TTL) {
        config.adapter = () => Promise.resolve({
          data: entry.data,
          status: 200,
          statusText: 'OK (cached)',
          headers: {},
          config,
        })
        return config
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：缓存成功的 GET 响应；写入操作清空缓存
api.interceptors.response.use(
  (response) => {
    const { config } = response

    // 写入类的请求 → 清空全部缓存（数据已变更）
    if (['post', 'put', 'delete', 'patch'].includes(config.method)) {
      cache.clear()
      persistCache()
    }

    // 缓存成功的 GET 响应（内存 + sessionStorage）
    if (config.method === 'get' && response.status === 200) {
      const key = cacheKey(config)
      cache.set(key, { data: response.data, time: Date.now() })
      persistCache()
    }

    return response.data
  },
  async (error) => {
    const { config, response } = error
    const auth = useAuthStore()

    // 401 且不是 refresh 请求本身，尝试刷新 token
    if (response?.status === 401 && auth.refreshToken && !config._retry) {
      if (!isRefreshing) {
        isRefreshing = true
        config._retry = true
        try {
          const res = await axios.post(`${BASE || '/api'}/user/refresh`, {
            refresh_token: auth.refreshToken,
          })
          if (res.data.code === 0) {
            auth.setToken(res.data.data.token)
            refreshQueue.forEach((cb) => cb(res.data.data.token))
            refreshQueue = []
            config.headers.Authorization = `Bearer ${res.data.data.token}`
            isRefreshing = false
            return api(config)
          }
          isRefreshing = false
          refreshQueue.forEach((cb) => cb(null))
          refreshQueue = []
          auth.logout()
          window.location.replace('/login')
          return new Promise(() => {})
        } catch (e) {
          isRefreshing = false
          refreshQueue.forEach((cb) => cb(null))
          refreshQueue = []
          auth.logout()
          window.location.replace('/login')
          return new Promise(() => {})
        }
      } else {
        return new Promise((resolve) => {
          refreshQueue.push((newToken) => {
            if (newToken) {
              config.headers.Authorization = `Bearer ${newToken}`
              resolve(api(config))
            }
          })
        })
      }
    }

    const msg = response?.data?.message || error.message || '网络错误'
    return Promise.reject(new Error(msg))
  }
)

// token 刷新队列
let isRefreshing = false
let refreshQueue = []

export default api
