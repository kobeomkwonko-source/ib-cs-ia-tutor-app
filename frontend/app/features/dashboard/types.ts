export type Task = {
  id: number
  title: string
  description: string | null
  deadline: string | null
  points: number
  pdf_path: string | null
  is_done?: boolean
}

export type LeaderboardRow = {
  username: string
  total_points: number
  rank: number
  tier: string
}

export type Submission = {
  id: number
  task_id: number
  student_id: number
  submitted_at: string
  text_content: string | null
  pdf_path: string | null
  student_comment: string | null
  teacher_comment: string | null
  awarded_points: number | null
  awarded_at: string | null
  max_points?: number
  days_late?: number
  attempt_number?: number
  username?: string
}

export type Reward = {
  id: number
  title: string
  description: string | null
  cost: number
}

export type Purchase = {
  id: number
  purchased_at: string
  cost_at_purchase: number
  title: string
  username?: string
  email?: string | null
}

export type StudentOverviewTask = {
  id: number
  title: string
  deadline: string | null
  submitted: boolean
  submitted_at: string | null
}

export type StudentOverview = {
  id: number
  username: string
  email: string | null
  points: number
  tasks: StudentOverviewTask[]
}
