import { NavLink, Outlet } from "react-router"

import { cn } from "~/lib/utils"

export default function TutorLayout() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <header className="border-b bg-gray-50 px-4 py-3">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="font-bold">Teacher Portal</div>
          <nav className="flex items-center gap-2 text-sm">
            <NavButton to="/tutor/dashboard">Dashboard</NavButton>
            <NavButton to="/tutor/login">Teacher Login</NavButton>
            <NavButton to="/tutor/register">Teacher Register</NavButton>
          </nav>
        </div>
      </header>

      <main className="px-4 py-8">
        <div className="mx-auto w-full max-w-4xl rounded border bg-white p-6 shadow-sm">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function NavButton({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "rounded px-3 py-1",
          isActive ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-200"
        )
      }
    >
      {children}
    </NavLink>
  )
}
