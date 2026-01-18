import { useCallback, useState } from "react"
import { redirect, useLoaderData, useNavigate } from "react-router"

import type { User } from "~/features/auth/types"
import { StudentDashboard } from "~/features/dashboard/components/student-dashboard"
import { api, getApiErrorMessage } from "~/lib/api"
import { fetchSession } from "~/lib/session"

export async function loader({ request }: { request: Request }) {
  const user = await fetchSession(request)
  if (!user || user.role !== "student") {
    return redirect("/student/login")
  }
  return user
}

export default function StudentDashboardRoute() {
  const user = useLoaderData() as User
  const [currentUser, setCurrentUser] = useState<User>(user)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleLogout = async () => {
    setStatusMessage(null)
    try {
      await api.post("/logout")
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to log out."))
    } finally {
      navigate("/student/login")
    }
  }

  const handlePointsUpdate = useCallback((points: number) => {
    setCurrentUser((prev) => ({ ...prev, points }))
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded border bg-gray-50 px-4 py-3">
        <div>
          <p className="text-sm text-gray-600">Signed in as</p>
          <h2 className="text-xl font-semibold">{currentUser.username}</h2>
          <p className="text-sm text-gray-700">
            Role: Student · Points: {currentUser.points}
          </p>
        </div>
        <button
          className="rounded border px-3 py-1 text-sm text-gray-700"
          onClick={handleLogout}
        >
          Log out
        </button>
      </div>
      {statusMessage ? <p className="text-sm text-red-600">{statusMessage}</p> : null}

      <StudentDashboard
        user={currentUser}
        onPointsUpdate={handlePointsUpdate}
      />
    </div>
  )
}
