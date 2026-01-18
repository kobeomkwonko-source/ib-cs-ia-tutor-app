import { useCallback, useEffect, useMemo, useState } from "react"

import { Button } from "~/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card"
import { Input } from "~/components/ui/input"
import { Label } from "~/components/ui/label"
import { Textarea } from "~/components/ui/textarea"
import { API_BASE_URL, api, getApiErrorMessage } from "~/lib/api"
import type { User } from "~/features/auth/types"
import type { Purchase, Reward, StudentOverview, Submission, Task } from "../types"
import { formatDeadline, toDatetimeLocal } from "../utils"

type Props = {
  user: User
}

type TaskDraft = {
  title: string
  description: string
  deadline: string
  points: string
  difficulty: "easy" | "medium" | "hard"
  assignedStudentIds: number[]
}

type StudentOption = {
  id: number
  username: string
  email: string | null
}

export function TutorDashboard({ user }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [taskDraft, setTaskDraft] = useState<TaskDraft>({
    title: "",
    description: "",
    deadline: "",
    points: "",
    difficulty: "medium",
    assignedStudentIds: [],
  })
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null)
  const [editingDraft, setEditingDraft] = useState<TaskDraft | null>(null)
  const [submissions, setSubmissions] = useState<Record<number, Submission[]>>({})
  const [awardDrafts, setAwardDrafts] = useState<
    Record<string, { points: string; comment: string }>
  >({})
  const [hiddenSubmissionGroups, setHiddenSubmissionGroups] = useState<
    Record<string, boolean>
  >({})
  const [rewardDraft, setRewardDraft] = useState({
    title: "",
    description: "",
    cost: "",
  })
  const [rewards, setRewards] = useState<Reward[]>([])
  const [rewardPurchases, setRewardPurchases] = useState<Purchase[]>([])
  const [rewardEdits, setRewardEdits] = useState<
    Record<number, { title: string; description: string; cost: string; active: boolean }>
  >({})
  const [students, setStudents] = useState<StudentOption[]>([])
  const [studentOverview, setStudentOverview] = useState<StudentOverview[]>([])
  const [studentSort, setStudentSort] = useState<"name-asc" | "name-desc">("name-asc")
  const [dueSort, setDueSort] = useState<"due-asc" | "due-desc">("due-asc")
  const [submissionFilter, setSubmissionFilter] = useState<
    "all" | "submitted" | "pending"
  >("all")
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [rewardStatusMessage, setRewardStatusMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fetchTasks = useCallback(async () => {
    try {
      const { data } = await api.get<{ tasks: Task[] }>("/tasks")
      setTasks(data.tasks || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load tasks."))
    }
  }, [])

  const fetchSubmissions = useCallback(async (taskId: number) => {
    try {
      const { data } = await api.get<{ submissions: Submission[] }>(
        `/tasks/${taskId}/submissions`
      )
      setSubmissions((prev) => ({ ...prev, [taskId]: data.submissions || [] }))
      setHiddenSubmissionGroups((prev) => {
        const next = { ...prev }
        Object.keys(next).forEach((key) => {
          if (key.startsWith(`${taskId}-`)) {
            delete next[key]
          }
        })
        return next
      })
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load submissions."))
    }
  }, [])

  const fetchRewards = useCallback(async () => {
    try {
      const { data } = await api.get<{ rewards: Reward[] }>("/rewards")
      setRewards(data.rewards || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load rewards."))
    }
  }, [])

  const fetchRewardPurchases = useCallback(async () => {
    try {
      const { data } = await api.get<{ purchases: Purchase[] }>("/purchases/all")
      setRewardPurchases(data.purchases || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load purchases."))
    }
  }, [])

  const fetchStudents = useCallback(async () => {
    try {
      const { data } = await api.get<{ students: StudentOption[] }>("/students/list")
      setStudents(data.students || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load students."))
    }
  }, [])

  const fetchStudentOverview = useCallback(async () => {
    try {
      const { data } = await api.get<{ students: StudentOverview[] }>("/students/overview")
      setStudentOverview(data.students || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load student overview."))
    }
  }, [])

  const fetchTaskAssignments = useCallback(async (taskId: number) => {
    try {
      const { data } = await api.get<{ studentIds: number[] }>(
        `/tasks/${taskId}/assignments`
      )
      return data.studentIds || []
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load task assignments."))
      return []
    }
  }, [])

  const handleCreateTask = async (event: React.FormEvent) => {
    event.preventDefault()
    setIsSubmitting(true)
    setStatusMessage(null)

    try {
      const { data } = await api.post("/tasks", {
        title: taskDraft.title,
        description: taskDraft.description,
        deadline: taskDraft.deadline || null,
        points: Number(taskDraft.points),
        difficulty: taskDraft.difficulty,
        assignedStudentIds: taskDraft.assignedStudentIds,
      })
      setStatusMessage(data.message || "Task created.")
      setTaskDraft({
        title: "",
        description: "",
        deadline: "",
        points: "",
        difficulty: "medium",
        assignedStudentIds: [],
      })
      fetchTasks()
      fetchStudentOverview()
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to create task."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEditTask = async (task: Task) => {
    setEditingTaskId(task.id)
    const assignedStudentIds = await fetchTaskAssignments(task.id)
    setEditingDraft({
      title: task.title,
      description: task.description || "",
      deadline: toDatetimeLocal(task.deadline),
      points: String(task.points),
      difficulty: task.difficulty,
      assignedStudentIds,
    })
  }

  const handleSaveTask = async (taskId: number) => {
    if (!editingDraft) return
    setIsSubmitting(true)
    try {
      const { data } = await api.put(`/tasks/${taskId}`, {
        title: editingDraft.title,
        description: editingDraft.description,
        deadline: editingDraft.deadline || null,
        points: Number(editingDraft.points),
        difficulty: editingDraft.difficulty,
        assignedStudentIds: editingDraft.assignedStudentIds,
      })
      setStatusMessage(data.message || "Task updated.")
      setEditingTaskId(null)
      setEditingDraft(null)
      fetchTasks()
      fetchStudentOverview()
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to update task."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteTask = async (taskId: number) => {
    const confirmed = window.confirm("Delete this homework? This cannot be undone.")
    if (!confirmed) return
    setStatusMessage(null)
    try {
      const { data } = await api.delete(`/tasks/${taskId}`)
      setStatusMessage(data.message || "Task deleted.")
      fetchTasks()
      fetchStudentOverview()
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to delete task."))
    }
  }

  const handleAward = async (
    taskId: number,
    studentId: number,
    awardedPoints: number,
    comment: string
  ) => {
    setStatusMessage(null)
    try {
      const { data } = await api.post(`/tasks/${taskId}/students/${studentId}/award`, {
        awardedPoints,
        comment,
      })
      setStatusMessage(data.message || "Points awarded.")
      setHiddenSubmissionGroups((prev) => ({
        ...prev,
        [`${taskId}-${studentId}`]: true,
      }))
      fetchTasks()
      fetchStudentOverview()
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to award points."))
    }
  }

  const handleAwardDraftChange = (
    groupKey: string,
    field: "points" | "comment",
    value: string
  ) => {
    setAwardDrafts((prev) => ({
      ...prev,
      [groupKey]: {
        points: prev[groupKey]?.points ?? "",
        comment: prev[groupKey]?.comment ?? "",
        [field]: value,
      },
    }))
  }

  const handleCreateReward = async (event: React.FormEvent) => {
    event.preventDefault()
    setIsSubmitting(true)
    setStatusMessage(null)
    setRewardStatusMessage(null)
    try {
      const { data } = await api.post("/rewards", {
        title: rewardDraft.title,
        description: rewardDraft.description,
        cost: Number(rewardDraft.cost),
      })
      setRewardStatusMessage(data.message || "Add reward completed.")
      setRewardDraft({ title: "", description: "", cost: "" })
      fetchRewards()
    } catch (error) {
      setRewardStatusMessage(getApiErrorMessage(error, "Failed to create reward."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUpdateReward = async (reward: Reward, updates: Partial<Reward>) => {
    setStatusMessage(null)
    setRewardStatusMessage(null)
    try {
      await api.put(`/rewards/${reward.id}`, updates)
      setRewardStatusMessage("Save completed.")
      fetchRewards()
    } catch (error) {
      setRewardStatusMessage(getApiErrorMessage(error, "Failed to update reward."))
    }
  }

  const handleDeleteReward = async (rewardId: number) => {
    setStatusMessage(null)
    setRewardStatusMessage(null)
    const confirmed = window.confirm("Delete this reward? This cannot be undone.")
    if (!confirmed) return
    try {
      const { data } = await api.delete(`/rewards/${rewardId}`)
      setRewardStatusMessage(data.message || "Reward deleted.")
      fetchRewards()
    } catch (error) {
      setRewardStatusMessage(getApiErrorMessage(error, "Failed to delete reward."))
    }
  }

  useEffect(() => {
    fetchTasks()
    fetchRewards()
    fetchStudents()
    fetchStudentOverview()
    fetchRewardPurchases()
  }, [fetchRewardPurchases, fetchRewards, fetchStudentOverview, fetchStudents, fetchTasks])

  const toggleDraftStudent = (studentId: number) => {
    setTaskDraft((prev) => {
      const next = prev.assignedStudentIds.includes(studentId)
        ? prev.assignedStudentIds.filter((id) => id !== studentId)
        : [...prev.assignedStudentIds, studentId]
      return { ...prev, assignedStudentIds: next }
    })
  }

  const toggleEditingStudent = (studentId: number) => {
    setEditingDraft((prev) => {
      if (!prev) return prev
      const next = prev.assignedStudentIds.includes(studentId)
        ? prev.assignedStudentIds.filter((id) => id !== studentId)
        : [...prev.assignedStudentIds, studentId]
      return { ...prev, assignedStudentIds: next }
    })
  }

  const submissionStats = useMemo(() => {
    const stats: Record<number, { submittedCount: number; assignedCount: number }> = {}
    studentOverview.forEach((student) => {
      student.tasks.forEach((task) => {
        if (!stats[task.id]) {
          stats[task.id] = { submittedCount: 0, assignedCount: 0 }
        }
        stats[task.id].assignedCount += 1
        if (task.submitted) {
          stats[task.id].submittedCount += 1
        }
      })
    })
    return stats
  }, [studentOverview])

  const sortedStudents = useMemo(() => {
    const sorted = [...studentOverview]
    sorted.sort((a, b) => {
      const nameA = a.username.toLowerCase()
      const nameB = b.username.toLowerCase()
      if (nameA === nameB) return 0
      const result = nameA < nameB ? -1 : 1
      return studentSort === "name-asc" ? result : -result
    })
    return sorted
  }, [studentOverview, studentSort])

  const filterAndSortTasks = useCallback(
    (tasksList: StudentOverview["tasks"]) => {
      const filtered =
        submissionFilter === "all"
          ? tasksList
          : tasksList.filter((task) =>
              submissionFilter === "submitted" ? task.submitted : !task.submitted
            )
      const sorted = [...filtered]
      sorted.sort((a, b) => {
        const timeA = a.deadline ? new Date(a.deadline).getTime() : null
        const timeB = b.deadline ? new Date(b.deadline).getTime() : null
        if (timeA === null && timeB === null) return 0
        if (timeA === null) return dueSort === "due-asc" ? 1 : -1
        if (timeB === null) return dueSort === "due-asc" ? -1 : 1
        const result = timeA - timeB
        return dueSort === "due-asc" ? result : -result
      })
      return sorted
    },
    [dueSort, submissionFilter]
  )

  const rewardPurchasesByStudent = useMemo(() => {
    return rewardPurchases.reduce((groups, purchase) => {
      const name = purchase.username || "Unknown student"
      const email = purchase.email || ""
      const key = `${name}||${email}`
      if (!groups[key]) {
        groups[key] = { name, email, purchases: [] as Purchase[] }
      }
      groups[key].purchases.push(purchase)
      return groups
    }, {} as Record<string, { name: string; email: string; purchases: Purchase[] }>)
  }, [rewardPurchases])

  return (
    <div className="space-y-4">
      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Create homework</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleCreateTask}>
            <div className="space-y-1 text-left">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={taskDraft.title}
                onChange={(e) => setTaskDraft((prev) => ({ ...prev, title: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-1 text-left">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                rows={3}
                value={taskDraft.description}
                onChange={(e) =>
                  setTaskDraft((prev) => ({ ...prev, description: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1 text-left">
              <Label htmlFor="deadline">Deadline (KST)</Label>
              <Input
                id="deadline"
                type="datetime-local"
                value={taskDraft.deadline}
                onChange={(e) =>
                  setTaskDraft((prev) => ({ ...prev, deadline: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-2 text-left">
              <div className="flex items-center justify-between gap-2">
                <Label>Assign to students</Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-8 px-3 text-xs"
                    onClick={() =>
                      setTaskDraft((prev) => ({
                        ...prev,
                        assignedStudentIds: students.map((student) => student.id),
                      }))
                    }
                  >
                    Select all
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="h-8 px-3 text-xs"
                    onClick={() =>
                      setTaskDraft((prev) => ({ ...prev, assignedStudentIds: [] }))
                    }
                  >
                    Clear
                  </Button>
                </div>
              </div>
              {students.length === 0 ? (
                <p className="text-sm text-gray-600">No students available.</p>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {students.map((student) => (
                    <label
                      key={student.id}
                      className="flex items-center gap-2 rounded border px-2 py-1 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={taskDraft.assignedStudentIds.includes(student.id)}
                        onChange={() => toggleDraftStudent(student.id)}
                      />
                      <span>{student.username}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1 text-left">
                <Label htmlFor="points">Points</Label>
                <Input
                  id="points"
                  type="number"
                  value={taskDraft.points}
                  onChange={(e) =>
                    setTaskDraft((prev) => ({ ...prev, points: e.target.value }))
                  }
                  required
                />
              </div>
              <div className="space-y-1 text-left">
                <Label htmlFor="difficulty">Difficulty</Label>
                <select
                  id="difficulty"
                  className="w-full rounded border px-3 py-2 text-sm"
                  value={taskDraft.difficulty}
                  onChange={(e) =>
                    setTaskDraft((prev) => ({
                      ...prev,
                      difficulty: e.target.value as TaskDraft["difficulty"],
                    }))
                  }
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create task"}
            </Button>
          </form>
        </CardContent>
        {statusMessage ? <CardFooter className="text-sm text-gray-700">{statusMessage}</CardFooter> : null}
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Homework list</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {tasks.length === 0 ? (
            <p className="text-sm text-gray-700">No tasks created yet.</p>
          ) : (
            <ul className="space-y-4">
              {tasks.map((task) => (
                <li key={task.id} className="rounded border p-3 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="text-left">
                      <p className="font-semibold">{task.title}</p>
                      <p className="text-sm text-gray-700">{task.description}</p>
                      <p className="text-xs text-gray-600">
                        Points: {task.points} · Difficulty: {task.difficulty}
                      </p>
                      <p className="text-xs text-gray-600">Deadline: {formatDeadline(task.deadline)}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => handleEditTask(task)}>
                        Edit
                      </Button>
                      <Button variant="destructive" onClick={() => handleDeleteTask(task.id)}>
                        Delete
                      </Button>
                    </div>
                  </div>

                  {editingTaskId === task.id && editingDraft ? (
                    <div className="space-y-2">
                      <Input
                        value={editingDraft.title}
                        onChange={(e) =>
                          setEditingDraft((prev) =>
                            prev ? { ...prev, title: e.target.value } : prev
                          )
                        }
                      />
                      <Textarea
                        rows={3}
                        value={editingDraft.description}
                        onChange={(e) =>
                          setEditingDraft((prev) =>
                            prev ? { ...prev, description: e.target.value } : prev
                          )
                        }
                      />
                      <Input
                        type="datetime-local"
                        value={editingDraft.deadline}
                        onChange={(e) =>
                          setEditingDraft((prev) =>
                            prev ? { ...prev, deadline: e.target.value } : prev
                          )
                        }
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <Input
                          type="number"
                          value={editingDraft.points}
                          onChange={(e) =>
                            setEditingDraft((prev) =>
                              prev ? { ...prev, points: e.target.value } : prev
                            )
                          }
                        />
                        <select
                          className="w-full rounded border px-3 py-2 text-sm"
                          value={editingDraft.difficulty}
                          onChange={(e) =>
                            setEditingDraft((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    difficulty: e.target.value as TaskDraft["difficulty"],
                                  }
                                : prev
                            )
                          }
                        >
                          <option value="easy">Easy</option>
                          <option value="medium">Medium</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>
                      <div className="space-y-2 text-left">
                        <div className="flex items-center justify-between gap-2">
                          <Label>Assigned students</Label>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              className="h-8 px-3 text-xs"
                              onClick={() =>
                                setEditingDraft((prev) =>
                                  prev
                                    ? {
                                        ...prev,
                                        assignedStudentIds: students.map(
                                          (student) => student.id
                                        ),
                                      }
                                    : prev
                                )
                              }
                            >
                              Select all
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              className="h-8 px-3 text-xs"
                              onClick={() =>
                                setEditingDraft((prev) =>
                                  prev ? { ...prev, assignedStudentIds: [] } : prev
                                )
                              }
                            >
                              Clear
                            </Button>
                          </div>
                        </div>
                        {students.length === 0 ? (
                          <p className="text-sm text-gray-600">No students available.</p>
                        ) : (
                          <div className="grid gap-2 sm:grid-cols-2">
                            {students.map((student) => (
                              <label
                                key={student.id}
                                className="flex items-center gap-2 rounded border px-2 py-1 text-sm"
                              >
                                <input
                                  type="checkbox"
                                  checked={editingDraft.assignedStudentIds.includes(
                                    student.id
                                  )}
                                  onChange={() => toggleEditingStudent(student.id)}
                                />
                                <span>{student.username}</span>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button onClick={() => handleSaveTask(task.id)} disabled={isSubmitting}>
                          Save
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingTaskId(null)
                            setEditingDraft(null)
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <Button
                        variant={
                          (submissionStats[task.id]?.submittedCount || 0) > 0
                            ? "default"
                            : "outline"
                        }
                        className={
                          (submissionStats[task.id]?.submittedCount || 0) > 0
                            ? ""
                            : "text-gray-600"
                        }
                        onClick={() => fetchSubmissions(task.id)}
                        type="button"
                      >
                        Load submissions
                      </Button>
                      <span className="text-xs text-gray-600">
                        Submitted: {submissionStats[task.id]?.submittedCount || 0}/
                        {submissionStats[task.id]?.assignedCount || 0}
                      </span>
                    </div>
                    <div className="mt-2 space-y-2 text-sm">
                      {submissions[task.id] === undefined ? (
                        <p className="text-gray-600">
                          {(submissionStats[task.id]?.submittedCount || 0) > 0
                            ? "Submissions available. Click load to view."
                            : "No submissions yet."}
                        </p>
                      ) : submissions[task.id].length === 0 ? (
                        <p className="text-gray-600">No submissions yet.</p>
                      ) : (
                        Object.values(
                          (submissions[task.id] || []).reduce(
                            (groups, submission) => {
                              const key = `${task.id}-${submission.student_id}`
                              if (!groups[key]) {
                                groups[key] = {
                                  key,
                                  studentId: submission.student_id,
                                  username: submission.username || "Student",
                                  submissions: [],
                                }
                              }
                              groups[key].submissions.push(submission)
                              return groups
                            },
                            {} as Record<
                              string,
                              {
                                key: string
                                studentId: number
                                username: string
                                submissions: Submission[]
                              }
                            >
                          )
                        ).map((group) => {
                          if (hiddenSubmissionGroups[group.key]) return null
                          const latest = group.submissions[0]
                          const draft = awardDrafts[group.key] || {
                            points: latest.awarded_points?.toString() || "",
                            comment: latest.teacher_comment || "",
                          }

                          return (
                            <div key={group.key} className="rounded border p-2 space-y-2">
                              <div className="flex items-center justify-between">
                                <p className="text-sm font-semibold">{group.username}</p>
                                <span className="text-xs text-gray-600">
                                  {group.submissions.length} submissions
                                </span>
                              </div>
                              <div className="space-y-2">
                                {group.submissions.map((submission) => (
                                  <div key={submission.id} className="rounded border p-2">
                                    <p className="text-xs text-gray-600">
                                      {submission.submitted_at}
                                      {submission.attempt_number
                                        ? ` · Attempt ${submission.attempt_number}`
                                        : ""}
                                    </p>
                                    <p className="text-xs text-gray-600">
                                      Max points: {submission.max_points} · Days late:{" "}
                                      {submission.days_late}
                                    </p>
                                    {submission.text_content ? (
                                      <p className="text-xs text-gray-700">
                                        Text: {submission.text_content}
                                      </p>
                                    ) : null}
                                    {submission.student_comment ? (
                                      <p className="text-xs text-gray-700">
                                        Student comment: {submission.student_comment}
                                      </p>
                                    ) : null}
                                    {submission.pdf_path ? (
                                      <a
                                        className="mt-2 inline-block text-xs text-blue-600 underline"
                                        href={`${API_BASE_URL}/submissions/${submission.id}/file`}
                                      >
                                        Download PDF
                                      </a>
                                    ) : null}
                                  </div>
                                ))}
                              </div>
                              <div className="space-y-2">
                                <Input
                                  type="number"
                                  placeholder="Adjust points"
                                  value={draft.points}
                                  onChange={(e) =>
                                    handleAwardDraftChange(group.key, "points", e.target.value)
                                  }
                                />
                                <Input
                                  placeholder="Teacher comment"
                                  value={draft.comment}
                                  onChange={(e) =>
                                    handleAwardDraftChange(group.key, "comment", e.target.value)
                                  }
                                />
                                <div className="flex gap-2">
                                  <Button
                                    onClick={() =>
                                      handleAward(
                                        task.id,
                                        group.studentId,
                                        Number(draft.points || 0),
                                        draft.comment
                                      )
                                    }
                                  >
                                    Save award
                                  </Button>
                                  <Button
                                    variant="outline"
                                    onClick={() => {
                                      setAwardDrafts((prev) => {
                                        const next = { ...prev }
                                        delete next[group.key]
                                        return next
                                      })
                                      setHiddenSubmissionGroups((prev) => ({
                                        ...prev,
                                        [group.key]: true,
                                      }))
                                    }}
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            </div>
                          )
                        })
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Student list</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex flex-wrap gap-2 text-sm">
            <label className="flex items-center gap-2">
              <span className="text-gray-600">Student sort</span>
              <select
                className="rounded border px-2 py-1 text-sm"
                value={studentSort}
                onChange={(event) =>
                  setStudentSort(event.target.value as "name-asc" | "name-desc")
                }
              >
                <option value="name-asc">Name A-Z</option>
                <option value="name-desc">Name Z-A</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-gray-600">Due date</span>
              <select
                className="rounded border px-2 py-1 text-sm"
                value={dueSort}
                onChange={(event) =>
                  setDueSort(event.target.value as "due-asc" | "due-desc")
                }
              >
                <option value="due-asc">Oldest first</option>
                <option value="due-desc">Newest first</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-gray-600">Filter</span>
              <select
                className="rounded border px-2 py-1 text-sm"
                value={submissionFilter}
                onChange={(event) =>
                  setSubmissionFilter(
                    event.target.value as "all" | "submitted" | "pending"
                  )
                }
              >
                <option value="all">All</option>
                <option value="submitted">Submitted</option>
                <option value="pending">Pending</option>
              </select>
            </label>
          </div>
          {studentOverview.length === 0 ? (
            <p className="text-sm text-gray-700">No students yet.</p>
          ) : (
            <ul className="space-y-3">
              {sortedStudents.map((student) => {
                const submittedCount = student.tasks.filter((task) => task.submitted).length
                const visibleTasks = filterAndSortTasks(student.tasks)
                return (
                  <li key={student.id} className="rounded border p-3 text-left space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{student.username}</p>
                        <p className="text-xs text-gray-600">
                          {student.email || "No email"}
                        </p>
                      </div>
                      <span className="text-xs text-gray-600">
                        {submittedCount}/{student.tasks.length} submitted · {student.points} pts
                      </span>
                    </div>
                  {student.tasks.length === 0 ? (
                    <p className="text-xs text-gray-600">No assigned homework.</p>
                  ) : (
                    <ul className="space-y-1 text-xs">
                      {visibleTasks.length === 0 ? (
                        <li className="text-xs text-gray-500">
                          No homework matches this filter.
                        </li>
                      ) : (
                        visibleTasks.map((task) => (
                        <li
                          key={task.id}
                          className="flex items-center justify-between gap-2 rounded border px-2 py-1"
                        >
                          <div className="flex flex-col">
                            <span className="flex items-center gap-2">
                              <span
                                className={`h-2 w-2 rounded-full ${
                                  task.submitted ? "bg-green-500" : "bg-amber-500"
                                }`}
                              />
                              {task.title}
                            </span>
                            <span className="text-[11px] text-gray-500">
                              {task.submitted
                                ? `Submitted at ${task.submitted_at || "unknown"}`
                                : "Not submitted"}
                            </span>
                          </div>
                          <span
                            className={
                              task.submitted ? "text-green-600" : "text-amber-600"
                            }
                          >
                            {task.submitted ? "Submitted" : "Pending"}
                          </span>
                        </li>
                        ))
                      )}
                    </ul>
                  )}
                </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Reward shop management</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={handleCreateReward}>
            <Input
              placeholder="Reward title"
              value={rewardDraft.title}
              onChange={(e) => setRewardDraft((prev) => ({ ...prev, title: e.target.value }))}
              required
            />
            <Input
              placeholder="Description"
              value={rewardDraft.description}
              onChange={(e) => setRewardDraft((prev) => ({ ...prev, description: e.target.value }))}
            />
            <Input
              type="number"
              placeholder="Cost"
              value={rewardDraft.cost}
              onChange={(e) => setRewardDraft((prev) => ({ ...prev, cost: e.target.value }))}
              required
            />
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Add reward"}
            </Button>
          </form>
          <div className="mt-4 space-y-2">
            {rewards.length === 0 ? (
              <p className="text-sm text-gray-700">No rewards yet.</p>
            ) : (
              rewards.map((reward) => {
                const edit = rewardEdits[reward.id] || {
                  title: reward.title,
                  description: reward.description || "",
                  cost: String(reward.cost),
                  active: Boolean(reward.active),
                }

                return (
                  <div key={reward.id} className="rounded border p-2 text-left space-y-2">
                    <Input
                      value={edit.title}
                      onChange={(e) =>
                        setRewardEdits((prev) => ({
                          ...prev,
                          [reward.id]: { ...edit, title: e.target.value },
                        }))
                      }
                    />
                    <Input
                      value={edit.description}
                      onChange={(e) =>
                        setRewardEdits((prev) => ({
                          ...prev,
                          [reward.id]: { ...edit, description: e.target.value },
                        }))
                      }
                    />
                    <Input
                      type="number"
                      value={edit.cost}
                      onChange={(e) =>
                        setRewardEdits((prev) => ({
                          ...prev,
                          [reward.id]: { ...edit, cost: e.target.value },
                        }))
                      }
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() =>
                          handleUpdateReward(reward, {
                            title: edit.title,
                            description: edit.description,
                            cost: Number(edit.cost),
                          })
                        }
                      >
                        Save
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          const nextActive = !edit.active
                          setRewardEdits((prev) => ({
                            ...prev,
                            [reward.id]: { ...edit, active: nextActive },
                          }))
                          handleUpdateReward(reward, { active: nextActive ? 1 : 0 })
                        }}
                      >
                        {edit.active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => handleDeleteReward(reward.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </CardContent>
        {rewardStatusMessage ? (
          <CardFooter className="text-sm text-gray-700">{rewardStatusMessage}</CardFooter>
        ) : null}
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Reward purchases</CardTitle>
        </CardHeader>
        <CardContent>
          {rewardPurchases.length === 0 ? (
            <p className="text-sm text-gray-700">No purchases yet.</p>
          ) : (
            <div className="space-y-3 text-left text-sm">
              {Object.values(rewardPurchasesByStudent).map((group) => (
                <div key={`${group.name}-${group.email}`} className="rounded border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">{group.name}</p>
                    <p className="text-xs text-gray-600">
                      {group.email || "No email"}
                    </p>
                  </div>
                  <ul className="mt-2 space-y-2">
                    {group.purchases.map((purchase) => (
                      <li key={purchase.id} className="rounded border p-2">
                        <p className="font-medium">{purchase.title}</p>
                        <p className="text-xs text-gray-600">
                          {purchase.cost_at_purchase} points · {purchase.purchased_at}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
