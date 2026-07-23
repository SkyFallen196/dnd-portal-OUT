import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";
import RoleTags from "./RoleTags";

// Общая рамка с верхней навигацией для внутренних страниц.
// Тумблера «Режим редактирования» здесь нет специально: он влияет только на действия
// внутри комнаты, поэтому живёт в шапке самой комнаты (RoomPage).
export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      <nav className="nav">
        <span className="brand">⚔ D&D Portal</span>
        <Link to="/rooms">Комнаты</Link>
        <Link to="/heroes">Свиток героя</Link>
        {user?.role === "admin" && <Link to="/admin">Админ-панель</Link>}
        <span className="spacer" />

        <Link to="/profile" className="badge" title="Профиль и смена пароля">
          {user?.username} <RoleTags user={user} />
        </Link>
        <button className="secondary small" onClick={onLogout}>
          Выйти
        </button>
      </nav>
      <div className="container">
        <Outlet />
      </div>
    </>
  );
}
