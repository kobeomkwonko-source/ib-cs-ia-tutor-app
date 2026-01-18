import { redirect } from "react-router"

import { fetchSession } from "~/lib/session"

export async function loader({ request }: { request: Request }) {
  const user = await fetchSession(request)
  if (user?.role === "student") {
    return redirect("/student/dashboard")
  }
  return redirect("/student/login")
}

export default function StudentIndexRedirect() {
  return null
}
