import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { useAuth } from "../store/auth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const login = useAuth((s) => s.login);
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      // Бэкенд ждёт форму OAuth2 (поля username/password).
      const form = new URLSearchParams({ username, password });
      const { data } = await api.post("/auth/login", form);
      await login(data.access_token);
      navigate("/");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <div className="panel auth-card">
        <h1>D&D Portal</h1>
        <p className="muted" style={{ marginTop: -8, marginBottom: 18 }}>✧ Назови себя, странник ✧</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>✧ Имя странника ✧</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="имя или ворон-почта"
              autoFocus
            />
          </div>
          <div className="field">
            <label>✧ Тайное слово ✧</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="*****"
            />
          </div>
          <button type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Отворяем врата…" : "Войти"}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Впервые здесь? <Link to="/register">Впиши имя в летопись</Link>
        </p>
        <p className="muted" style={{ marginTop: 6, fontSize: "0.8rem", opacity: 0.7 }}>
          ⚔ Забыл тайное слово? Проси хранителя портала (администратора) назначить новое ⚔
        </p>
      </div>
    </div>
  );
}
