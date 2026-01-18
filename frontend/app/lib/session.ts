import type { User } from "~/features/auth/types"
import { API_BASE_URL } from "./api"

type SessionResponse =
  | {
      success: true
      userId: number
      username: string
      email?: string
      role: User["role"]
      points: number
    }
  | {
      success: false
      message?: string
    }

export async function fetchSession(request?: Request): Promise<User | null> {
  const headers: HeadersInit = {}
  const cookie = request?.headers.get("cookie")
  if (cookie) headers.cookie = cookie

  const response = await fetch(`${API_BASE_URL}/me`, {
    method: "GET",
    headers,
    credentials: "include",
  })

  if (!response.ok) return null

  const data = (await response.json()) as SessionResponse
  if (!data.success) return null

  return {
    userId: data.userId,
    username: data.username,
    email: data.email,
    role: data.role,
    points: data.points,
  }
}
