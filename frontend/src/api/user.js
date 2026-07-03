import api from './index'

export const userApi = {
  register(data) {
    return api.post('/user/register', data)
  },
  login(data) {
    return api.post('/user/login', data)
  },
  getMe() {
    return api.get('/user/me')
  },
  refresh(data) {
    return api.post('/user/refresh', data)
  },
  logout() {
    return api.post('/user/logout')
  },
  update(userId, data) {
    return api.put(`/user/${userId}`, data)
  },
  uploadAvatar(userId, formData) {
    return api.put(`/user/${userId}/avatar`, formData)
  },
  changePassword(userId, data) {
    return api.put(`/user/${userId}/password`, data)
  },
  getPublicProfile(identifier) {
    return api.get(`/user/${identifier}`)
  },
  getSolvedProblems(userId, params) {
    return api.get(`/user/${userId}/solved`, { params })
  },
  getUserProblems(userId, params) {
    return api.get(`/user/${userId}/problems`, { params })
  },
}
