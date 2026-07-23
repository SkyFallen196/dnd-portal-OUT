import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { hasActiveSubscription, useAuth } from "../store/auth";
import type { User } from "../api/types";

export default function ActivateCodePage() {
  const { user, setUser } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const active = hasActiveSubscription(user);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post<User>("/codes/activate", { code });
      setUser(data);
      navigate("/rooms");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1>Подписка / код доступа</h1>

      {active ? (
        <div className="success">
          Подписка активна до{" "}
          <b>{new Date(user!.subscription_expires_at!).toLocaleString("ru-RU")}</b>. Можно играть!
          <div style={{ marginTop: 10 }}>
            <button onClick={() => navigate("/rooms")}>Перейти к комнатам</button>
          </div>
        </div>
      ) : (
        <div className="banner">
          У вас пока нет активной подписки. Введите код доступа, полученный у администратора.
        </div>
      )}

      <div className="panel" style={{ maxWidth: 420, marginTop: 12 }}>
        <form onSubmit={submit}>
          {error && <div className="error">{error}</div>}
          <div className="field">
            <label>Код доступа</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="Например: 4XK9AB2C"
            />
          </div>
          <button type="submit" disabled={busy || !code}>
            {busy ? "Активируем…" : "Активировать код"}
          </button>
        </form>
      </div>
    </div>
  );
}
