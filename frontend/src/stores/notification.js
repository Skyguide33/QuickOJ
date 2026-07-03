import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi } from '../api/notifications'

export const useNotificationStore = defineStore('notification', () => {
  const unreadCount = ref(0)

  async function fetchUnreadCount() {
    try {
      const res = await notificationsApi.getUnreadCount()
      if (res.code === 0) {
        unreadCount.value = res.data.unread_count
      }
    } catch {
      // ignore
    }
  }

  function setUnreadCount(n) {
    unreadCount.value = n
  }

  function decrementUnread() {
    if (unreadCount.value > 0) unreadCount.value--
  }

  return { unreadCount, fetchUnreadCount, setUnreadCount, decrementUnread }
})
