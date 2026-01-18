import {
  type RouteConfig,
  index,
  layout,
  prefix,
  route,
} from "@react-router/dev/routes"

export default [
  index("routes/home.tsx"),
  layout(
    "./routes/student/layout.tsx",
    prefix("student", [
      index("./routes/student/index.tsx"),
      route("login", "./routes/student/login.tsx"),
      route("register", "./routes/student/register.tsx"),
      route("dashboard", "./routes/student/dashboard.tsx"),
    ])
  ),
  layout(
    "./routes/tutor/layout.tsx",
    prefix("tutor", [
      index("./routes/tutor/index.tsx"),
      route("login", "./routes/tutor/login.tsx"),
      route("register", "./routes/tutor/register.tsx"),
      route("dashboard", "./routes/tutor/dashboard.tsx"),
    ])
  ),
] satisfies RouteConfig
