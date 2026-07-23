import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { useAuth } from "../store/auth";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
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
      const { data } = await api.post("/auth/register", { username, email, password });
      await login(data.access_token);
      navigate("/activate"); // сразу ведём активировать код-подписку
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <div className="panel auth-card">
        <h1>Впиши имя в летопись</h1>
        <p className="muted" style={{ marginTop: -8, marginBottom: 18 }}>
          ✧ Создавая героя, ты принимаешь судьбу ✧
        </p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>✧ Имя героя ✧ (мин. 3 руны)</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Как тебя назовут в летописях?"
              autoFocus
            />
          </div>
          <div className="field">
            <label>✧ Ворон-почта ✧</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="куда слать вести" />
          </div>
          <div className="field">
            <label>✧ Тайное слово ✧ (мин. 6 рун)</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="минимум 6 рун" />
          </div>
          <button type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Скрепляем судьбу…" : "Создать"}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Уже вписан в летопись? <Link to="/login">Войти в портал</Link>
        </p>
      </div>
    </div>
  );
}
