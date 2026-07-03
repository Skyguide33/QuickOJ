import api from './index'

export const submissionsApi = {
  getList(params, skipCache) {
    return api.get('/submissions', { params, ...(skipCache ? { _skipCache: true } : {}) })
  },
  getDetail(submissionId, skipCache) {
    return api.get(`/submissions/${submissionId}`, { ...(skipCache ? { _skipCache: true } : {}) })
  },
  getStatus(submissionId) {
    return api.get(`/submissions/${submissionId}/status`, { _skipCache: true })
  },
}
