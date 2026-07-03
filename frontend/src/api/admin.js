import api from './index'

export const adminApi = {
  getUsers(params) {
    return api.get('/admin/users', { params })
  },
  changeUserRole(userId, role) {
    return api.put(`/admin/users/${userId}/role`, null, { params: { role } })
  },
  changeUserStatus(userId, status, reason) {
    return api.put(`/admin/users/${userId}/status`, null, {
      params: { status, ...(reason ? { reason } : {}) },
    })
  },
  changeProblemStatus(problemId, status, reviewComment) {
    return api.put(`/admin/problems/${problemId}/status`, null, {
      params: { status, ...(reviewComment ? { review_comment: reviewComment } : {}) },
    })
  },
  sendNotification(title, content, { userId, username } = {}) {
    const params = { title, content }
    if (userId) params.target_user_id = userId
    else if (username) params.target_username = username
    return api.post('/admin/notifications', null, { params })
  },
  getJudgeStatus(skipCache) {
    return api.get('/admin/judge', { ...(skipCache ? { _skipCache: true } : {}) })
  },
  connectJudge(cutoff) {
    const params = {}
    if (cutoff) params.cutoff = cutoff
    return api.post('/admin/judge/connect', null, { params })
  },
  disconnectJudge() {
    return api.post('/admin/judge/disconnect')
  },
}
