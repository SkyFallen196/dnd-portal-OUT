import { Navigate } from "react-router-dom";
import { hasActiveSubscription, useAuth } from "../store/auth";

interface Props {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requireSubscription?: boolean;
}

// Оборачивает страницы, доступные только авторизованным (и, по флагам, только
// админам или только с активной подпиской).
export default function ProtectedRoute({ children, requireAdmin, requireSubscription }: Props) {
  const user = useAuth((s) => s.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (requireAdmin && user.role !== "admin") {
    return <Navigate to="/" replace />;
  }
  if (requireSubscription && !hasActiveSubscription(user)) {
    return <Navigate to="/activate" replace />;
  }
  return <>{children}</>;
}
