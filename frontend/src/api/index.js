import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res.data
  },
  error => {
    const isTimeout = error?.code === 'ECONNABORTED'
    const requestUrl = String(error?.config?.url || '')
    const isBackgroundLlmAction = /\/raw-issues\/\d+\/(translate|analyze)$/.test(requestUrl)

    if (isTimeout && isBackgroundLlmAction) {
      ElMessage.warning('请求超时，后台可能仍在执行。请稍后刷新查看结果。')
      const timeoutError = new Error('BACKGROUND_RUNNING_AFTER_TIMEOUT')
      timeoutError.isBackgroundTimeout = true
      timeoutError.cause = error
      return Promise.reject(timeoutError)
    }

    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default api
