import { redirect } from "react-router"

import { fetchSession } from "~/lib/session"

export async function loader({ request }: { request: Request }) {
  const user = await fetchSession(request)
  if (user?.role === "tutor") {
    return redirect("/tutor/dashboard")
  }
  return redirect("/tutor/login")
}

export default function TutorIndexRedirect() {
  return null
}
