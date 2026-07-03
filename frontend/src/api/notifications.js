import api from './index'

export const notificationsApi = {
  getList(params) {
    return api.get('/notifications', { params })
  },
  getUnreadCount() {
    return api.get('/notifications/unread-count')
  },
  markRead(notificationId) {
    return api.put(`/notifications/${notificationId}/read`)
  },
  markAllRead() {
    return api.put('/notifications/read-all')
  },
  delete(notificationId) {
    return api.delete(`/notifications/${notificationId}`)
  },
}
