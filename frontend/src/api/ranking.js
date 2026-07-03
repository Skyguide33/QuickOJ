import api from './index'

export const rankingApi = {
  getList(params) {
    return api.get('/ranking', { params })
  },
}
