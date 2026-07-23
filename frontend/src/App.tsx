import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./store/auth";
import { getToken } from "./api/client";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ActivateCodePage from "./pages/ActivateCodePage";
import RoomsPage from "./pages/RoomsPage";
import RoomPage from "./pages/RoomPage";
import AdminPage from "./pages/AdminPage";
import HeroesPage from "./pages/HeroesPage";
import ProfilePage from "./pages/ProfilePage";

export default function App() {
  const { fetchMe, loading } = useAuth();

  useEffect(() => {
    // При загрузке приложения пытаемся восстановить сессию по токену.
    if (getToken()) {
      fetchMe();
    } else {
      useAuth.setState({ loading: false });
    }
  }, [fetchMe]);

  if (loading) {
    return <div className="center-screen">Загрузка…</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Экран игровой комнаты — во весь экран, без общей рамки */}
      <Route
        path="/rooms/:roomId"
        element={
          <ProtectedRoute requireSubscription>
            <RoomPage />
          </ProtectedRoute>
        }
      />

      {/* Остальные защищённые страницы — с верхней навигацией */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/rooms" replace />} />
        <Route path="/activate" element={<ActivateCodePage />} />
        <Route path="/heroes" element={<HeroesPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/rooms"
          element={
            <ProtectedRoute requireSubscription>
              <RoomsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <AdminPage />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
