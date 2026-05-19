// Route guard: ensures user is logged in. Optionally restricts to allowed roles.

import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import type { UserRole } from "@/types";

interface Props {
  children: React.ReactNode;
  roles?: UserRole[];
}

export function RequireAuth({ children, roles }: Props) {
  const { user, accessToken } = useAuthStore();
  const location = useLocation();

  if (!accessToken || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
