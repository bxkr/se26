import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { strings } from "../lib/strings";

export function ProtectedRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-ink-muted">
        {strings.common.loading}
      </div>
    );
  }

  if (!user) return <Navigate to="/" replace />;

  return <Outlet />;
}
