import axios, { type AxiosRequestConfig } from "axios"

const FALLBACK_BASE_URL = "http://127.0.0.1:5001"

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString().trim() || FALLBACK_BASE_URL

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
  withCredentials: true,
})

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
  withCredentials: true,
})

type RetryConfig = AxiosRequestConfig & { _retry?: boolean }

let isRefreshing = false
let refreshQueue: Array<(success: boolean) => void> = []

function resolveRefreshQueue(success: boolean) {
  refreshQueue.forEach((callback) => callback(success))
  refreshQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status
    const originalRequest = error?.config as RetryConfig | undefined

    if (!originalRequest || status !== 401) {
      return Promise.reject(error)
    }

    const url = originalRequest.url || ""
    if (originalRequest._retry || url.includes("/refresh") || url.includes("/login")) {
      return Promise.reject(error)
    }

    originalRequest._retry = true

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push((success) => {
          if (!success) return reject(error)
          resolve(api(originalRequest))
        })
      })
    }

    isRefreshing = true
    try {
      await refreshClient.post("/refresh")
      resolveRefreshQueue(true)
      return api(originalRequest)
    } catch (refreshError) {
      resolveRefreshQueue(false)
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

// error handling
export function getApiErrorMessage(error: unknown, fallback = "Something went wrong.") {
  if (!error) return fallback

  if (axios.isAxiosError(error)) {
    const message =
      (error.response?.data as { message?: string } | undefined)?.message ||
      error.message
    return message || fallback
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}
