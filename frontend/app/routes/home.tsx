import { Link } from "react-router"

import { Button } from "~/components/ui/button"

export default function Home() {
  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <h1 className="text-3xl font-bold">Homework helper</h1>
      <p className="text-sm text-gray-700">Student access</p>
      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link to="/student/login">Student login</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/student/register">Student register</Link>
        </Button>
      </div>
    </main>
  )
}
