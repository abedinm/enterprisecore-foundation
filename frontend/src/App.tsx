import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/RequireAuth";

import LoginPage from "@/pages/auth/Login";
import RegisterPage from "@/pages/auth/Register";
import ForgotPasswordPage from "@/pages/auth/ForgotPassword";
import DashboardPage from "@/pages/Dashboard";
import SettingsPage from "@/pages/Settings";
import NotificationsPage from "@/pages/Notifications";
import UsersPage from "@/pages/Users";
import ProjectsPage from "@/pages/Projects";
import TasksPage from "@/pages/Tasks";
import DepartmentsPage from "@/pages/Departments";
import AuditPage from "@/pages/AuditLog";
import ApiKeysPage from "@/pages/ApiKeys";

import { useAuthStore } from "@/store/auth";
import { api } from "@/api/client";

export default function App() {
  // On a fresh page load, if we have a token but no user, fetch /auth/me to hydrate.
  const { accessToken, user, setUser, logout } = useAuthStore();

  useEffect(() => {
    if (accessToken && !user) {
      api.get("/auth/me").then((r) => setUser(r.data)).catch(() => logout());
    }
  }, [accessToken, user, setUser, logout]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route element={<RequireAuth><AppShell /></RequireAuth>}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/users" element={<RequireAuth roles={["admin"]}><UsersPage /></RequireAuth>} />
        <Route path="/departments" element={<RequireAuth roles={["admin","manager"]}><DepartmentsPage /></RequireAuth>} />
        <Route path="/audit" element={<RequireAuth roles={["admin"]}><AuditPage /></RequireAuth>} />
        <Route path="/api-keys" element={<RequireAuth roles={["admin","developer"]}><ApiKeysPage /></RequireAuth>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
