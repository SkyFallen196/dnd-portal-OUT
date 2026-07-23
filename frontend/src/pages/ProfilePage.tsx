import { useState } from "react";
import { api, errorMessage, setToken } from "../api/client";
import { useAuth } from "../store/auth";
import RoleTags from "../components/RoleTags";

// Личный кабинет: данные аккаунта и смена пароля.
export default function ProfilePage() {
  const user = useAuth((s) => s.user);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setOk("");
    if (next.length < 6) {
      setError("Новый пароль должен быть не короче 6 символов");
      return;
    }
    if (next !== repeat) {
      setError("Новый пароль и повтор не совпадают");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<{ access_token: string }>("/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      // Сервер выдаёт свежий токен — подменяем сохранённый.
      setToken(data.access_token);
      setCurrent("");
      setNext("");
      setRepeat("");
      setOk("Пароль изменён.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1>Профиль</h1>

      <div className="panel" style={{ marginBottom: 16 }}>
        <p style={{ margin: "0 0 6px" }}>
          <b>{user?.username}</b> <RoleTags user={user} />
        </p>
        <p className="muted" style={{ margin: "0 0 6px" }}>{user?.email}</p>
        <p className="muted" style={{ margin: 0 }}>
          Подписка:{" "}
          {user?.subscription_expires_at
            ? `до ${new Date(user.subscription_expires_at).toLocaleDateString("ru-RU")}`
            : user?.role === "admin"
              ? "не нужна (администратор)"
              : "нет"}
        </p>
      </div>

      <div className="panel" style={{ maxWidth: 420 }}>
        <h3 style={{ marginTop: 0 }}>🔑 Смена пароля</h3>
        {error && <div className="error">{error}</div>}
        {ok && <div className="badge" style={{ display: "block", marginBottom: 12 }}>{ok}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Текущий пароль</label>
            <input
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Новый пароль</label>
            <input
              type="password"
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Повторите новый пароль</label>
            <input
              type="password"
              autoComplete="new-password"
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
            />
          </div>
          <button type="submit" disabled={busy || !current || !next || !repeat}>
            {busy ? "Меняю…" : "Сменить пароль"}
          </button>
        </form>
        <p className="muted" style={{ marginBottom: 0, marginTop: 12 }}>
          Забыли пароль? Почтовой рассылки в портале нет — попросите администратора сбросить его
          в админ-панели, а потом смените здесь на свой.
        </p>
      </div>
    </div>
  );
}
