import api from './index'

export const problemsApi = {
  getList(params) {
    return api.get('/problems', { params })
  },
  getDetail(problemId) {
    return api.get(`/problems/${problemId}`)
  },
  submit(problemId, formData) {
    return api.post(`/problems/${problemId}/submit`, formData)
  },
  debug(problemId, formData) {
    return api.post(`/problems/${problemId}/debug`, formData)
  },
  getDebugResult(jobId) {
    return api.get(`/problems/debug/result/${jobId}`)
  },
  create(formData) {
    return api.post('/problems', formData)
  },
  update(problemId, formData) {
    return api.put(`/problems/${problemId}`, formData)
  },
  delete(problemId) {
    return api.delete(`/problems/${problemId}`)
  },
}
