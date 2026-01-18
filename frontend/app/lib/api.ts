import axios from "axios"

const FALLBACK_BASE_URL = "http://127.0.0.1:5001"

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString().trim() || FALLBACK_BASE_URL

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
  withCredentials: true,
})

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
