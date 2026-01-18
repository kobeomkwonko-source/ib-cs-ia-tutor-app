export type UserRole = "tutor" | "student"

export type User = {
  userId: number
  username: string
  email?: string
  role: UserRole
  points: number
}

export type AuthSuccessResponse = {
  success: true
  message?: string
  userId: number
  username: string
  email?: string
  role: UserRole
  points: number
}

export type AuthErrorResponse = {
  success: false
  message?: string
}
