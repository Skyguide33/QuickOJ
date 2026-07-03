import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const refreshToken = ref('')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value && ['root', 'admin'].includes(user.value.role))
  const isRoot = computed(() => user.value?.role === 'root')
  const role = computed(() => user.value?.role || 'guest')

  function setAuth(data) {
    token.value = data.token
    refreshToken.value = data.refresh_token
    user.value = data.user
  }

  function setToken(newToken) {
    token.value = newToken
  }

  function setUser(u) {
    user.value = u
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
  }

  return {
    token,
    refreshToken,
    user,
    isLoggedIn,
    isAdmin,
    isRoot,
    role,
    setAuth,
    setToken,
    setUser,
    logout,
  }
}, {
  persist: {
    key: 'oj-auth',
    storage: localStorage,
    pick: ['token', 'refreshToken', 'user'],
  },
})
