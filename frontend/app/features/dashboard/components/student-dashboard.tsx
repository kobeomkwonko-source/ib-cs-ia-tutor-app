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
import type { LeaderboardRow, Purchase, Reward, Submission, Task } from "../types"
import { formatDeadline, getCountdown } from "../utils"

type Props = {
  user: User
  onPointsUpdate: (points: number) => void
}

type SubmissionDraft = {
  textContent: string
  file: File | null
}

type DeadlineMeta = {
  label: string
  className: string
  isPast: boolean
}

function parseKstDate(deadline: string) {
  const normalized = deadline.includes("T") ? deadline : deadline.replace(" ", "T")
  return new Date(`${normalized}+09:00`)
}

function getDeadlineMeta(deadline: string | null | undefined): DeadlineMeta {
  if (!deadline) {
    return {
      label: "No deadline",
      className: "bg-gray-100 text-gray-600 border border-gray-200",
      isPast: false,
    }
  }

  const deadlineDate = parseKstDate(deadline)
  if (Number.isNaN(deadlineDate.getTime())) {
    return {
      label: "Invalid date",
      className: "bg-gray-100 text-gray-600 border border-gray-200",
      isPast: false,
    }
  }

  const now = new Date()
  const diffMs = deadlineDate.getTime() - now.getTime()
  if (diffMs <= 0) {
    return {
      label: "Past deadline",
      className: "bg-red-100 text-red-700 border border-red-200",
      isPast: true,
    }
  }

  const daysLeft = Math.max(0, Math.ceil(diffMs / 86400000))
  let className = "bg-emerald-100 text-emerald-700 border border-emerald-200"
  if (daysLeft <= 1) {
    className = "bg-red-100 text-red-700 border border-red-200"
  } else if (daysLeft <= 3) {
    className = "bg-orange-100 text-orange-700 border border-orange-200"
  } else if (daysLeft <= 5) {
    className = "bg-amber-100 text-amber-700 border border-amber-200"
  } else if (daysLeft <= 7) {
    className = "bg-yellow-100 text-yellow-700 border border-yellow-200"
  }

  return {
    label: `D-${daysLeft}`,
    className,
    isPast: false,
  }
}

function getDifficultyClass(difficulty?: string | null) {
  const normalized = (difficulty || "").toLowerCase()
  if (normalized === "easy") return "bg-emerald-100 text-emerald-700 border border-emerald-200"
  if (normalized === "medium") return "bg-amber-100 text-amber-700 border border-amber-200"
  if (normalized === "hard" || normalized === "difficult") {
    return "bg-red-100 text-red-700 border border-red-200"
  }
  return "bg-gray-100 text-gray-600 border border-gray-200"
}

function getTierClass(tier?: string | null) {
  const normalized = (tier || "").toLowerCase()
  if (normalized === "iron") return "bg-stone-200 text-stone-700 border border-stone-300"
  if (normalized === "bronze") return "bg-amber-200 text-amber-900 border border-amber-300"
  if (normalized === "silver") return "bg-slate-200 text-slate-700 border border-slate-300"
  if (normalized === "gold") return "bg-yellow-200 text-yellow-900 border border-yellow-300"
  if (normalized === "platinum") return "bg-teal-200 text-teal-900 border border-teal-300"
  if (normalized === "emerald") return "bg-emerald-200 text-emerald-900 border border-emerald-300"
  if (normalized === "diamond") return "bg-sky-200 text-sky-900 border border-sky-300"
  if (normalized === "master") return "bg-fuchsia-200 text-fuchsia-900 border border-fuchsia-300"
  if (normalized === "grandmaster") return "bg-rose-200 text-rose-900 border border-rose-300"
  if (normalized === "challenger") return "bg-indigo-200 text-indigo-900 border border-indigo-300"
  return "bg-gray-100 text-gray-600 border border-gray-200"
}

export function StudentDashboard({ user, onPointsUpdate }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([])
  const [rewards, setRewards] = useState<Reward[]>([])
  const [purchases, setPurchases] = useState<Purchase[]>([])
  const [submissions, setSubmissions] = useState<Record<number, Submission[]>>({})
  const [submissionStatus, setSubmissionStatus] = useState<Record<number, "none" | "some">>({})
  const [expandedTasks, setExpandedTasks] = useState<Record<number, boolean>>({})
  const [drafts, setDrafts] = useState<Record<number, SubmissionDraft>>({})
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [rewardStatusMessage, setRewardStatusMessage] = useState<string | null>(null)
  const [loadingTasks, setLoadingTasks] = useState(true)
  const [submittingTaskId, setSubmittingTaskId] = useState<number | null>(null)

  const fetchTasks = useCallback(async () => {
    setLoadingTasks(true)
    try {
      const { data } = await api.get<{ tasks: Task[] }>("/tasks")
      setTasks(data.tasks || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load tasks."))
    } finally {
      setLoadingTasks(false)
    }
  }, [])

  const fetchLeaderboard = useCallback(async () => {
    try {
      const { data } = await api.get<{ leaderboard: LeaderboardRow[] }>("/leaderboard")
      setLeaderboard(data.leaderboard || [])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load leaderboard."))
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

  const fetchPurchases = useCallback(async () => {
    try {
      const { data } = await api.get<{ purchases: Purchase[] }>("/purchases")
      setPurchases(data.purchases || [])
    } catch {
      // silent
    }
  }, [])

  const fetchSubmissions = useCallback(async (taskId: number) => {
    try {
      const { data } = await api.get<{ submissions: Submission[] }>("/submissions", {
        params: { taskId },
      })
      const nextSubmissions = data.submissions || []
      setSubmissions((prev) => ({ ...prev, [taskId]: nextSubmissions }))
      setSubmissionStatus((prev) => ({
        ...prev,
        [taskId]: nextSubmissions.length > 0 ? "some" : "none",
      }))
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to load submissions."))
    }
  }, [])

  const refreshUserPoints = useCallback(async () => {
    try {
      const { data } = await api.get<{
        success: boolean
        points?: number
      }>("/student-progress")
      if (data.success && typeof data.points === "number") {
        onPointsUpdate(data.points)
      }
    } catch {
      // silent
    }
  }, [onPointsUpdate])

  const handleToggleSubmissions = (taskId: number) => {
    setExpandedTasks((prev) => {
      const next = { ...prev, [taskId]: !prev[taskId] }
      return next
    })
    if (!expandedTasks[taskId] && submissionStatus[taskId] !== "none") {
      fetchSubmissions(taskId)
    }
  }

  const handleDraftChange = (taskId: number, field: keyof SubmissionDraft, value: string | File | null) => {
    setDrafts((prev) => ({
      ...prev,
        [taskId]: {
          textContent: prev[taskId]?.textContent || "",
          file: prev[taskId]?.file || null,
          [field]: value,
        },
    }))
  }

  const handleSubmitTask = async (taskId: number) => {
    setSubmittingTaskId(taskId)
    setStatusMessage(null)

    const draft = drafts[taskId] || { textContent: "", file: null }
    const formData = new FormData()
    formData.append("taskId", String(taskId))
    if (draft.textContent) formData.append("textContent", draft.textContent)
    if (draft.file) formData.append("pdf", draft.file)

    try {
      const { data } = await api.post("/submissions", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setStatusMessage(data.message || "Submission completed.")
      setDrafts((prev) => ({
        ...prev,
        [taskId]: { textContent: "", file: null },
      }))
      await Promise.all([fetchTasks(), fetchLeaderboard(), fetchSubmissions(taskId), refreshUserPoints()])
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Submission failed."))
    } finally {
      setSubmittingTaskId(null)
    }
  }

  const handlePurchase = async (rewardId: number) => {
    setRewardStatusMessage(null)
    const reward = rewards.find((item) => item.id === rewardId)
    if (!reward) {
      setRewardStatusMessage("Reward not found.")
      return
    }
    if (user.points < reward.cost) {
      setRewardStatusMessage("too small points")
      return
    }
    const confirmed = window.confirm("Buy this reward?")
    if (!confirmed) return
    try {
      const { data } = await api.post(`/rewards/${rewardId}/purchase`)
      setRewardStatusMessage(data.message || "Purchase complete.")
      await Promise.all([fetchRewards(), fetchPurchases(), refreshUserPoints()])
    } catch (error) {
      setRewardStatusMessage(getApiErrorMessage(error, "Purchase failed."))
    }
  }

  const groupedSubmissions = useMemo(() => submissions, [submissions])
  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) || null,
    [selectedTaskId, tasks]
  )
  const selectedDeadlineMeta = useMemo(
    () => (selectedTask ? getDeadlineMeta(selectedTask.deadline) : null),
    [selectedTask]
  )
  const latestSubmission = useMemo(() => {
    if (!selectedTaskId) return null
    const taskSubmissions = submissions[selectedTaskId] || []
    return taskSubmissions[0] || null
  }, [selectedTaskId, submissions])
  const latestTeacherComment = useMemo(() => {
    if (!selectedTaskId) return null
    const taskSubmissions = submissions[selectedTaskId] || []
    const withComment = taskSubmissions.find((submission) => submission.teacher_comment)
    return withComment?.teacher_comment || null
  }, [selectedTaskId, submissions])

  useEffect(() => {
    fetchTasks()
    fetchLeaderboard()
    fetchRewards()
    fetchPurchases()
    refreshUserPoints()
  }, [fetchLeaderboard, fetchPurchases, fetchRewards, fetchTasks, refreshUserPoints])

  useEffect(() => {
    if (selectedTaskId === null) return
    if (submissionStatus[selectedTaskId]) return
    fetchSubmissions(selectedTaskId)
  }, [fetchSubmissions, selectedTaskId, submissionStatus])

  return (
    <div className="space-y-4">
      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Homework list</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingTasks ? (
            <p className="text-sm text-gray-700">Loading tasks...</p>
          ) : tasks.length === 0 ? (
            <p className="text-sm text-gray-700">No homework yet.</p>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-semibold text-gray-700">Pending homework</p>
                {tasks.filter((task) => !task.is_done).length === 0 ? (
                  <p className="text-sm text-gray-600">No pending homework.</p>
                ) : (
                  <ul className="space-y-3">
                    {tasks.filter((task) => !task.is_done).map((task) => {
                      const deadlineMeta = getDeadlineMeta(task.deadline)
                      const difficultyClass = getDifficultyClass(task.difficulty)
                      const deadlineTextClass = deadlineMeta.isPast
                        ? "text-red-700"
                        : "text-gray-600"
                      const itemClass = deadlineMeta.isPast
                        ? "border-red-200 bg-red-50/40"
                        : "border-gray-200 bg-white"
                      return (
                        <li key={task.id} className={`rounded border ${itemClass}`}>
                          <button
                            type="button"
                            onClick={() => setSelectedTaskId(task.id)}
                            className="flex w-full flex-col gap-2 rounded px-4 py-3 text-left transition hover:bg-gray-50"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="text-base font-semibold">{task.title}</p>
                                <p className="text-sm text-gray-700">
                                  {task.description || "No description."}
                                </p>
                              </div>
                              <span
                                className={`rounded-full px-2 py-1 text-xs font-semibold ${deadlineMeta.className}`}
                              >
                                {deadlineMeta.label}
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                              <span className="text-gray-600">Points: {task.points}</span>
                              <span
                                className={`rounded-full px-2 py-0.5 font-semibold ${difficultyClass}`}
                              >
                                {task.difficulty || "Unknown"}
                              </span>
                              <span className={deadlineTextClass}>
                                Deadline (KST): {formatDeadline(task.deadline)}
                              </span>
                              <span className={deadlineTextClass}>
                                Countdown: {getCountdown(task.deadline)}
                              </span>
                            </div>
                            <div className="text-xs text-gray-500">
                              Pending · Click to open submission
                            </div>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-gray-700">Submitted homework</p>
                {tasks.filter((task) => task.is_done).length === 0 ? (
                  <p className="text-sm text-gray-600">No submitted homework.</p>
                ) : (
                  <ul className="space-y-3">
                    {tasks.filter((task) => task.is_done).map((task) => {
                      const deadlineMeta = getDeadlineMeta(task.deadline)
                      const difficultyClass = getDifficultyClass(task.difficulty)
                      const submittedMeta = {
                        label: "Submitted",
                        className: "bg-emerald-100 text-emerald-700 border border-emerald-200",
                      }
                      const deadlineTextClass = "text-gray-600"
                      const itemClass = "border-gray-200 bg-white"
                      return (
                        <li key={task.id} className={`rounded border ${itemClass}`}>
                          <button
                            type="button"
                            onClick={() => setSelectedTaskId(task.id)}
                            className="flex w-full flex-col gap-2 rounded px-4 py-3 text-left transition hover:bg-gray-50"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="text-base font-semibold">{task.title}</p>
                                <p className="text-sm text-gray-700">
                                  {task.description || "No description."}
                                </p>
                              </div>
                              <span
                                className={`rounded-full px-2 py-1 text-xs font-semibold ${submittedMeta.className}`}
                              >
                                {submittedMeta.label}
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                              <span className="text-gray-600">Points: {task.points}</span>
                              <span
                                className={`rounded-full px-2 py-0.5 font-semibold ${difficultyClass}`}
                              >
                                {task.difficulty || "Unknown"}
                              </span>
                              <span className={deadlineTextClass}>
                                Deadline (KST): {formatDeadline(task.deadline)}
                              </span>
                              <span className={deadlineTextClass}>
                                {deadlineMeta.isPast ? "Submitted" : `Countdown: ${getCountdown(task.deadline)}`}
                              </span>
                            </div>
                            <div className="text-xs text-gray-500">
                              Done · Click to open submission
                            </div>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </div>
          )}
        </CardContent>
        {statusMessage ? <CardFooter className="text-sm text-gray-700">{statusMessage}</CardFooter> : null}
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          {leaderboard.length === 0 ? (
            <p className="text-sm text-gray-700">No students yet.</p>
          ) : (
            <ol className="space-y-2 text-left">
              {leaderboard.map((row) => (
                <li key={`${row.username}-${row.rank}`} className="rounded border px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{row.username}</p>
                      <p className="text-xs text-gray-600">
                        {row.total_points} points · Tier: {row.tier}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${getTierClass(row.tier)}`}>
                        {row.tier}
                      </span>
                      <span className="text-sm text-gray-600">#{row.rank}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Reward shop</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {rewards.length === 0 ? (
            <p className="text-sm text-gray-700">No rewards yet.</p>
          ) : (
            <ul className="space-y-2">
              {rewards.map((reward) => {
                const canPurchase = user.points >= reward.cost
                return (
                  <li key={reward.id} className="rounded border p-3 text-left">
                    <p className="font-semibold">{reward.title}</p>
                    <p className="text-sm text-gray-700">
                      {reward.description || "No description."}
                    </p>
                    <p className="text-xs text-gray-600">Cost: {reward.cost} points</p>
                    <Button
                      onClick={() => handlePurchase(reward.id)}
                      variant={canPurchase ? "default" : "outline"}
                      className={
                        canPurchase
                          ? "mt-2 bg-black text-white hover:bg-black/90"
                          : "mt-2 bg-white text-gray-800 hover:bg-white"
                      }
                    >
                      Purchase
                    </Button>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
        {rewardStatusMessage ? (
          <CardFooter className="text-sm text-gray-700">{rewardStatusMessage}</CardFooter>
        ) : null}
      </Card>

      <Card className="border">
        <CardHeader>
          <CardTitle className="text-lg">Purchase history</CardTitle>
        </CardHeader>
        <CardContent>
          {purchases.length === 0 ? (
            <p className="text-sm text-gray-700">No purchases yet.</p>
          ) : (
            <ul className="space-y-2 text-left text-sm">
              {purchases.map((purchase) => (
                <li key={purchase.id} className="rounded border p-2">
                  <p>{purchase.title}</p>
                  <p className="text-xs text-gray-600">
                    {purchase.cost_at_purchase} points · {purchase.purchased_at}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {selectedTask ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="w-full max-w-2xl rounded-lg border bg-white shadow-lg">
            <div className="flex items-start justify-between border-b px-4 py-3">
              <div>
                <p className="text-lg font-semibold">{selectedTask.title}</p>
                <p className="text-sm text-gray-600">
                  Deadline (KST): {formatDeadline(selectedTask.deadline)}
                </p>
                {latestTeacherComment ? (
                  <p className="mt-1 text-sm text-gray-700">
                    Teacher comment: {latestTeacherComment}
                  </p>
                ) : null}
                {latestSubmission ? (
                  <div className="mt-2 space-y-1 text-sm text-gray-700">
                    <p className="text-xs text-gray-600">
                      Latest submission: {latestSubmission.submitted_at}
                    </p>
                    {latestSubmission.text_content ? (
                      <p>Submitted text: {latestSubmission.text_content}</p>
                    ) : null}
                    {latestSubmission.pdf_path ? (
                      <a
                        className="text-xs text-blue-600 underline"
                        href={`${API_BASE_URL}/submissions/${latestSubmission.id}/file`}
                      >
                        Download latest PDF
                      </a>
                    ) : null}
                  </div>
                ) : null}
              </div>
              <Button variant="outline" onClick={() => setSelectedTaskId(null)}>
                Close
              </Button>
            </div>

            <div className="space-y-4 px-4 py-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {selectedDeadlineMeta ? (
                  <span className={`rounded-full px-2 py-1 font-semibold ${selectedDeadlineMeta.className}`}>
                    {selectedDeadlineMeta.label}
                  </span>
                ) : null}
                <span className={`rounded-full px-2 py-0.5 font-semibold ${getDifficultyClass(selectedTask.difficulty)}`}>
                  {selectedTask.difficulty || "Unknown"}
                </span>
                <span className="text-gray-600">Points: {selectedTask.points}</span>
                <span className="text-gray-600">Countdown: {getCountdown(selectedTask.deadline)}</span>
              </div>

              <div className="space-y-2 text-left">
                <Label htmlFor={`text-${selectedTask.id}`}>Submission text / links</Label>
                <Textarea
                  id={`text-${selectedTask.id}`}
                  rows={3}
                  placeholder="Write your answer or paste links"
                  value={drafts[selectedTask.id]?.textContent || ""}
                  onChange={(e) => handleDraftChange(selectedTask.id, "textContent", e.target.value)}
                />
                <Label htmlFor={`pdf-${selectedTask.id}`}>PDF upload</Label>
                <Input
                  id={`pdf-${selectedTask.id}`}
                  type="file"
                  accept="application/pdf"
                  onChange={(e) =>
                    handleDraftChange(selectedTask.id, "file", e.target.files?.[0] ?? null)
                  }
                />
                <Button
                  type="button"
                  onClick={() => handleSubmitTask(selectedTask.id)}
                  disabled={submittingTaskId === selectedTask.id}
                >
                  {submittingTaskId === selectedTask.id ? "Submitting..." : "Submit"}
                </Button>
              </div>

              <div className="space-y-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleToggleSubmissions(selectedTask.id)}
                  disabled={submissionStatus[selectedTask.id] === "none"}
                >
                  {expandedTasks[selectedTask.id] ? "Hide submissions" : "View submissions"}
                </Button>
                {submissionStatus[selectedTask.id] === "none" ? (
                  <p className="text-xs text-gray-500">No submissions yet.</p>
                ) : null}
                {expandedTasks[selectedTask.id] ? (
                  <div className="space-y-2 text-sm">
                    {(groupedSubmissions[selectedTask.id] || []).length === 0 ? (
                      <p className="text-gray-600">No submissions yet.</p>
                    ) : (
                      (groupedSubmissions[selectedTask.id] || []).map((submission) => (
                        <div key={submission.id} className="rounded border p-2">
                          <p className="text-xs text-gray-600">
                            Submitted: {submission.submitted_at}
                            {submission.attempt_number
                              ? ` · Attempt ${submission.attempt_number}`
                              : ""}
                          </p>
                          <p className="text-xs text-gray-600">
                            Max points after penalty: {submission.max_points} · Days late:{" "}
                            {submission.days_late}
                          </p>
                          {submission.teacher_comment ? (
                            <p className="text-xs text-gray-700">
                              Teacher comment: {submission.teacher_comment}
                            </p>
                          ) : null}
                          {submission.awarded_points !== null ? (
                            <p className="text-xs text-gray-700">
                              Awarded: {submission.awarded_points} points
                            </p>
                          ) : null}
                          {submission.pdf_path ? (
                            <a
                              className="text-xs text-blue-600 underline"
                              href={`${API_BASE_URL}/submissions/${submission.id}/file`}
                            >
                              Download PDF
                            </a>
                          ) : null}
                        </div>
                      ))
                    )}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
