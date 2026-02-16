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
import { api, getApiErrorMessage } from "~/lib/api"

type FormState = {
  username: string
  email: string
  password: string
  confirmPassword: string
  isSubmitting: boolean
  error?: string | null
  success?: string | null
}

const initialState: FormState = {
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
  isSubmitting: false,
  error: null,
  success: null,
}

export default function StudentRegisterRoute() {
  const [form, setForm] = useState<FormState>(initialState)
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (form.password !== form.confirmPassword) {
      setForm((prev) => ({
        ...prev,
        error: "Passwords do not match.",
        success: null,
      }))
      return
    }

    setForm((prev) => ({ ...prev, isSubmitting: true, error: null, success: null }))

    try {
      const { data, status } = await api.post<{
        success: boolean
        message?: string
      }>("/register", {
        username: form.username,
        email: form.email,
        password: form.password,
        role: "student",
      })

      if ((status !== 201 && status !== 200) || !data.success) {
        setForm((prev) => ({
          ...prev,
          error: data.message || "Registration failed.",
          isSubmitting: false,
        }))
        return
      }

      setForm((prev) => ({
        ...prev,
        success: data.message || "Registration successful.",
        error: null,
        isSubmitting: false,
      }))

      setTimeout(() => navigate("/student/login"), 600)
    } catch (error) {
      setForm((prev) => ({
        ...prev,
        error: getApiErrorMessage(error, "Cannot connect to server."),
        isSubmitting: false,
      }))
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Register as student</h1>
      </div>

      <Card className="border">
        <CardContent className="pt-6">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1 text-left">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                name="username"
                placeholder="choose-a-username"
                autoComplete="username"
                value={form.username}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, username: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1 text-left">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="student@example.com"
                autoComplete="email"
                value={form.email}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, email: e.target.value }))
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
                autoComplete="new-password"
                placeholder="1234"
                value={form.password}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, password: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1 text-left">
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                placeholder="1234"
                value={form.confirmPassword}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    confirmPassword: e.target.value,
                  }))
                }
                required
              />
            </div>
            {form.error ? (
              <p className="text-sm text-red-600">{form.error}</p>
            ) : null}
            {form.success ? (
              <p className="text-sm text-green-600">{form.success}</p>
            ) : null}
            <Button
              className="w-full sm:w-auto"
              type="submit"
              disabled={form.isSubmitting}
            >
              {form.isSubmitting ? "Creating account..." : "Register"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="text-sm">
          <span className="text-gray-700">Already have an account?</span>
          <Button asChild variant="link" className="px-2">
            <Link to="/student/login">Go to login</Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
