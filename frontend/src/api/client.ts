import axios, { AxiosError } from 'axios'

interface Envelope<T> {
  code: number
  data: T
  message?: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public cause?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  paramsSerializer: (params) => {
    const search = new URLSearchParams()
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return
      if (Array.isArray(value)) value.forEach((item) => search.append(key, String(item)))
      else search.append(key, String(value))
    })
    return search.toString()
  },
})

api.interceptors.response.use(
  (response) => {
    const envelope = response.data as Envelope<unknown>
    if (envelope && typeof envelope === 'object' && 'code' in envelope) {
      if (envelope.code !== 200) throw new ApiError(envelope.message || '请求失败', response.status)
      return { ...response, data: envelope.data }
    }
    return response
  },
  (error: AxiosError<{ message?: string }>) => {
    const isBackgroundTimeout =
      error.code === 'ECONNABORTED' &&
      /\/raw-issues\/\d+\/translate$/.test(String(error.config?.url || ''))
    if (isBackgroundTimeout) {
      const timeoutError = new ApiError(
        '后台仍可能在执行，请稍后刷新查看结果',
        error.response?.status,
        error,
      )
      Object.assign(timeoutError, { backgroundRunning: true })
      throw timeoutError
    }
    throw new ApiError(
      error.response?.data?.message || error.message || '网络错误',
      error.response?.status,
      error,
    )
  },
)
