export function formatDeadline(deadline: string | null | undefined) {
  if (!deadline) return "No deadline set"

  const date = parseKst(deadline)
  if (Number.isNaN(date.getTime())) return "Invalid date"

  return date.toLocaleString("en-US", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  })
}

export function getCountdown(deadline: string | null | undefined) {
  if (!deadline) return "No deadline"
  const deadlineDate = parseKst(deadline)
  if (Number.isNaN(deadlineDate.getTime())) return "Invalid date"

  const now = new Date()
  const diffMs = deadlineDate.getTime() - now.getTime()
  if (diffMs <= 0) return "Past deadline"

  const totalSeconds = Math.floor(diffMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)

  if (days > 0) return `${days}d ${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function parseKst(deadline: string) {
  const normalized = deadline.includes("T")
    ? deadline
    : deadline.replace(" ", "T")
  return new Date(`${normalized}+09:00`)
}

export function toDatetimeLocal(deadline: string | null | undefined) {
  if (!deadline) return ""
  const date = parseKst(deadline)
  if (Number.isNaN(date.getTime())) return ""

  const pad = (value: number) => String(value).padStart(2, "0")
  const yyyy = date.getFullYear()
  const mm = pad(date.getMonth() + 1)
  const dd = pad(date.getDate())
  const hh = pad(date.getHours())
  const min = pad(date.getMinutes())

  return `${yyyy}-${mm}-${dd}T${hh}:${min}`
}
