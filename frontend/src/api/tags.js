import api from './index'

export const tagsApi = {
  getList(params) {
    return api.get('/tags', { params })
  },
}
