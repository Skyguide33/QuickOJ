/**
 * QuickOJ 前端全局配置
 * 所有可调参数集中管理，方便维护
 */

export const CONFIG = {
  // ---- 请求缓存 ----
  /** GET 请求内存缓存有效期 (ms) */
  REQUEST_CACHE_TTL: 30_000, // 30 秒

  // ---- 刷新冷却 ----
  /** 页面刷新冷却期 (ms)：在此时间内重复刷新不会重新请求后端 */
  REFRESH_COOLDOWN_MS: 3_000, // 3 秒

  /** sessionStorage 键名：上次页面加载时间戳 */
  REFRESH_COOLDOWN_KEY: 'qoj_last_load',

  // ---- 提交记录自动刷新 ----
  /** 提交记录列表自动刷新间隔 (ms) */
  SUBMISSION_REFRESH_INTERVAL: 3_000, // 3 秒

  // ---- 提交详情轮询 ----
  /** 提交详情页轮询间隔 (ms) */
  SUBMISSION_DETAIL_POLL_INTERVAL: 2_000, // 2 秒
  /** 提交详情页轮询最长持续时间 (ms) */
  SUBMISSION_DETAIL_POLL_TIMEOUT: 60_000, // 60 秒

  // ---- 调试结果轮询 ----
  /** 调试结果轮询间隔 (ms) */
  DEBUG_POLL_INTERVAL: 1_000, // 1 秒
}
