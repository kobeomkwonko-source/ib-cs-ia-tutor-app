import { useState } from "react"
import { redirect, useLoaderData, useNavigate } from "react-router"

import { Button } from "~/components/ui/button"
import type { User } from "~/features/auth/types"
import { TutorDashboard as DashboardView } from "~/features/dashboard/components/tutor-dashboard"
import { api, getApiErrorMessage } from "~/lib/api"
import { fetchSession } from "~/lib/session"

export async function loader({ request }: { request: Request }) {
  const user = await fetchSession(request)
  if (!user || user.role !== "tutor") {
    return redirect("/tutor/login")
  }
  return user
}

export default function TutorDashboardRoute() {
  const user = useLoaderData() as User
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleLogout = async () => {
    setStatusMessage(null)
    try {
      await api.post("/logout")
    } catch (error) {
      setStatusMessage(getApiErrorMessage(error, "Failed to log out."))
    } finally {
      navigate("/tutor/login")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded border bg-gray-50 px-4 py-3">
        <div>
          <p className="text-sm text-gray-600">Signed in as</p>
          <h2 className="text-xl font-semibold">{user.username}</h2>
          <p className="text-sm text-gray-700">Role: Teacher</p>
        </div>
        <Button onClick={handleLogout} variant="outline">
          Log out
        </Button>
      </div>
      {statusMessage ? <p className="text-sm text-red-600">{statusMessage}</p> : null}

      <DashboardView user={user} />
    </div>
  )
}
