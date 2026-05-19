// API types — kept in sync with backend Pydantic schemas.

export type UserRole = "admin" | "manager" | "employee" | "developer";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  avatar_url?: string | null;
  bio?: string | null;
  phone?: string | null;
  department_id?: number | null;
  last_login_at?: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type NotificationType = "info" | "success" | "warning" | "error" | "system";

export interface Notification {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  link?: string | null;
  read: boolean;
  created_at: string;
}

export interface Department {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export type ProjectStatus = "planning" | "active" | "on_hold" | "completed" | "archived";

export interface Project {
  id: number;
  name: string;
  description: string;
  status: ProjectStatus;
  owner_id: number;
  start_date?: string | null;
  end_date?: string | null;
  created_at: string;
  updated_at: string;
}

export type TaskStatus = "todo" | "in_progress" | "review" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  project_id: number;
  assignee_id?: number | null;
  due_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemSetting {
  id: number;
  key: string;
  value: string;
  description: string;
  updated_at: string;
}

export interface DashboardStats {
  users: { total: number; active: number; new_last_7d: number; by_role: Record<string, number> };
  projects: { total: number };
  tasks: { total: number; done: number; completion_rate: number };
  my_unread_notifications: number;
}
