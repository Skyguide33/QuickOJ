/**
 * 将后端返回的相对路径转为绝对 URL。
 * 本地开发用 Vite 代理，生产环境需拼接后端域名。
 */
export function assetUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  return base ? base + path : path
}

/**
 * 将 UTC 时间字符串转换为用户本地时间显示。
 * 数据库存 UTC，前端自动转为用户所在时区。
 */

export function formatDateTime(utcStr) {
  if (!utcStr) return '-'
  const d = new Date(utcStr + (utcStr.endsWith('Z') ? '' : 'Z'))
  if (isNaN(d.getTime())) return utcStr
  return d.toLocaleString('zh-CN', { hour12: false })
}

export function formatDate(utcStr) {
  if (!utcStr) return '-'
  const d = new Date(utcStr + (utcStr.endsWith('Z') ? '' : 'Z'))
  if (isNaN(d.getTime())) return utcStr.slice(0, 10)
  return d.toLocaleDateString('zh-CN')
}

export function formatTimeShort(utcStr) {
  if (!utcStr) return '-'
  const d = new Date(utcStr + (utcStr.endsWith('Z') ? '' : 'Z'))
  if (isNaN(d.getTime())) return utcStr.replace('T', ' ').slice(0, 19)
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${mo}-${day} ${h}:${mi}:${s}`
}