import { useState } from "react"
import { Link, useNavigate } from "react-router"

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
import type { User } from "~/features/auth/types"
import { api, getApiErrorMessage } from "~/lib/api"

type LoginFormState = {
  username: string
  password: string
  isSubmitting: boolean
  error?: string | null
}

const initialFormState: LoginFormState = {
  username: "",
  password: "",
  isSubmitting: false,
  error: null,
}

export default function TutorLoginRoute() {
  const [formState, setFormState] = useState<LoginFormState>(initialFormState)
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormState((prev) => ({ ...prev, isSubmitting: true, error: null }))

    try {
      const { data, status } = await api.post<{
        success: boolean
        message?: string
        userId: number
        username: string
        role: User["role"]
        points: number
      }>("/login", {
        username: formState.username,
        password: formState.password,
      })

      if (status !== 200 || !data.success) {
        setFormState((prev) => ({
          ...prev,
          error: data.message || "Login failed.",
          isSubmitting: false,
        }))
        return
      }

      if (data.role !== "tutor") {
        setFormState((prev) => ({
          ...prev,
          error: "This portal is for teachers. Please log in as a teacher.",
          isSubmitting: false,
        }))
        return
      }

      setFormState(initialFormState)
      navigate("/tutor/dashboard")
    } catch (error) {
      setFormState((prev) => ({
        ...prev,
        error: getApiErrorMessage(error, "Cannot connect to server."),
      }))
    } finally {
      setFormState((prev) => ({ ...prev, isSubmitting: false }))
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Teacher login</h1>
        <p className="text-sm text-gray-700">
          Sign in to manage homework for your students.
        </p>
      </div>

      <Card className="w-full border">
        <CardContent className="pt-6">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1 text-left">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                name="username"
                placeholder="teacher1"
                autoComplete="username"
                value={formState.username}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, username: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1 text-left">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                name="password"
                type="password"
                placeholder="1234"
                autoComplete="current-password"
                value={formState.password}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, password: e.target.value }))
                }
                required
              />
            </div>
            {formState.error ? (
              <p className="text-sm text-red-600">{formState.error}</p>
            ) : null}
            <Button
              className="w-full sm:w-auto"
              type="submit"
              disabled={formState.isSubmitting}
            >
              {formState.isSubmitting ? "Signing in..." : "Log in"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="text-sm">
          <span className="text-gray-700">Need an account?</span>
          <Button asChild variant="link" className="px-2">
            <Link to="/tutor/register">Register as teacher</Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
