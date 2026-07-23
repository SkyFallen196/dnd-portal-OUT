import { useEffect, useState } from "react";
import { adminEditOnce, api, errorMessage } from "../api/client";
import type { AccessCode, Role, Room, Token, User } from "../api/types";

type Tab = "users" | "codes" | "rooms" | "tokens";

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("users");
  return (
    <div>
      <h1>Админ-панель</h1>
      <div className="row" style={{ marginBottom: 16, flexWrap: "wrap" }}>
        <button className={tab === "users" ? "" : "secondary"} onClick={() => setTab("users")}>
          Пользователи
        </button>
        <button className={tab === "codes" ? "" : "secondary"} onClick={() => setTab("codes")}>
          Коды-подписки
        </button>
        <button className={tab === "rooms" ? "" : "secondary"} onClick={() => setTab("rooms")}>
          Комнаты
        </button>
        <button className={tab === "tokens" ? "" : "secondary"} onClick={() => setTab("tokens")}>
          Фишки на картах
        </button>
      </div>
      {tab === "users" && <UsersTab />}
      {tab === "codes" && <CodesTab />}
      {tab === "rooms" && <RoomsTab />}
      {tab === "tokens" && <TokensTab />}
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const { data } = await api.get<User[]>("/admin/users");
      setUsers(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => {
    load();
  }, []);

  const setRole = async (u: User, role: Role) => {
    try {
      await api.patch(`/admin/users/${u.id}`, { role });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  const setDm = async (u: User, is_dm: boolean) => {
    try {
      await api.patch(`/admin/users/${u.id}`, { is_dm });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  const toggleActive = async (u: User) => {
    try {
      await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  const grantMonth = async (u: User) => {
    const until = new Date();
    until.setDate(until.getDate() + 30);
    await api.patch(`/admin/users/${u.id}`, { subscription_expires_at: until.toISOString() });
    load();
  };
  const revokeSub = async (u: User) => {
    await api.patch(`/admin/users/${u.id}`, { subscription_expires_at: null });
    load();
  };
  // Почты в портале нет, поэтому «забыл пароль» решается так: админ ставит
  // временный пароль и передаёт его человеку, тот меняет его в своём профиле.
  const resetPassword = async (u: User) => {
    const pwd = prompt(`Новый временный пароль для ${u.username} (минимум 6 символов):`);
    if (pwd === null) return;
    if (pwd.length < 6) {
      setError("Пароль должен быть не короче 6 символов");
      return;
    }
    try {
      await api.post(`/admin/users/${u.id}/reset-password`, { new_password: pwd });
      setError("");
      alert(`Пароль для ${u.username} сброшен. Передайте его лично — пусть сменит в профиле.`);
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  const del = async (u: User) => {
    if (!confirm(`Удалить пользователя ${u.username}?`)) return;
    try {
      await api.delete(`/admin/users/${u.id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="panel">
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Пользователь</th>
            <th>Роль</th>
            <th title="Dungeon Master — мастер подземелий, ведёт игру">Мастер подземелий (DM)</th>
            <th>Подписка до</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>
                {u.username}
                <div className="muted">{u.email}</div>
              </td>
              <td>
                <select value={u.role} onChange={(e) => setRole(u, e.target.value as Role)}>
                  <option value="player">player</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>
                <label className="row" style={{ gap: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    style={{ width: "auto" }}
                    checked={u.is_dm}
                    onChange={(e) => setDm(u, e.target.checked)}
                  />
                  <span className="muted">может водить игры</span>
                </label>
              </td>
              <td>
                {u.subscription_expires_at
                  ? new Date(u.subscription_expires_at).toLocaleDateString("ru-RU")
                  : "—"}
                <div className="row" style={{ gap: 4, marginTop: 4 }}>
                  <button className="secondary small" onClick={() => grantMonth(u)}>
                    +30д
                  </button>
                  <button className="secondary small" onClick={() => revokeSub(u)}>
                    сбросить
                  </button>
                </div>
              </td>
              <td>{u.is_active ? "активен" : <span style={{ color: "#ff8a80" }}>заблокирован</span>}</td>
              <td>
                <div className="row" style={{ gap: 4 }}>
                  <button className="secondary small" onClick={() => toggleActive(u)}>
                    {u.is_active ? "Блок" : "Разблок"}
                  </button>
                  <button className="secondary small" title="Задать временный пароль" onClick={() => resetPassword(u)}>
                    🔑
                  </button>
                  <button className="small" onClick={() => del(u)}>
                    Удалить
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CodesTab() {
  const [codes, setCodes] = useState<AccessCode[]>([]);
  const [users, setUsers] = useState<Record<number, string>>({});
  const [days, setDays] = useState(30);
  const [count, setCount] = useState(1);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [c, u] = await Promise.all([
        api.get<AccessCode[]>("/codes"),
        api.get<User[]>("/admin/users"),
      ]);
      setCodes(c.data);
      setUsers(Object.fromEntries(u.data.map((x) => [x.id, x.username])));
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    try {
      await api.post("/codes", { duration_days: days, count });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const deleteCode = async (c: AccessCode) => {
    if (!confirm(`Удалить код ${c.code}? Если он был активирован, у пользователя вычтется ${c.duration_days} дн. подписки.`)) return;
    try {
      await api.delete(`/codes/${c.id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="panel">
      {error && <div className="error">{error}</div>}
      <div className="row" style={{ marginBottom: 16, flexWrap: "wrap" }}>
        <div>
          <label>Срок (дней)</label>
          <input type="number" value={days} min={1} onChange={(e) => setDays(Number(e.target.value))} style={{ width: 100 }} />
        </div>
        <div>
          <label>Сколько кодов</label>
          <input type="number" value={count} min={1} max={100} onChange={(e) => setCount(Number(e.target.value))} style={{ width: 100 }} />
        </div>
        <div style={{ alignSelf: "flex-end" }}>
          <button onClick={create}>Создать коды</button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Код</th>
            <th>Срок</th>
            <th>Статус</th>
            <th>Привязан к</th>
            <th>Активирован</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {codes.map((c) => (
            <tr key={c.id}>
              <td>
                <b>{c.code}</b>
              </td>
              <td>{c.duration_days} дн.</td>
              <td>{c.is_activated ? "использован" : <span className="tag dm">свободен</span>}</td>
              <td>{c.assigned_user_id ? users[c.assigned_user_id] ?? `#${c.assigned_user_id}` : "—"}</td>
              <td>{c.activated_at ? new Date(c.activated_at).toLocaleDateString("ru-RU") : "—"}</td>
              <td>
                <button className="small" onClick={() => deleteCode(c)}>
                  Удалить
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RoomsTab() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [users, setUsers] = useState<Record<number, string>>({});
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [r, u] = await Promise.all([
        api.get<Room[]>("/admin/rooms"),
        api.get<User[]>("/admin/users"),
      ]);
      setRooms(r.data);
      setUsers(Object.fromEntries(u.data.map((x) => [x.id, x.username])));
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => {
    load();
  }, []);

  const del = async (r: Room) => {
    if (!confirm(`Удалить комнату «${r.name}»? Будут удалены её карта, фишки и история бросков.`)) return;
    try {
      // Из админ-панели комнаты почти всегда чужие, поэтому разрешение шлём сразу.
      await api.delete(`/rooms/${r.id}`, adminEditOnce);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="panel">
      {error && <div className="error">{error}</div>}
      {rooms.length === 0 ? (
        <p className="muted">Комнат пока нет.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Название</th>
              <th>Мастер</th>
              <th>Код</th>
              <th>Создана</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rooms.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{users[r.dm_id] ?? `#${r.dm_id}`}</td>
                <td>{r.invite_code}</td>
                <td>{new Date(r.created_at).toLocaleDateString("ru-RU")}</td>
                <td>
                  <button className="small" onClick={() => del(r)}>
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function TokensTab() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const { data } = await api.get<Token[]>("/admin/tokens");
      setTokens(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  useEffect(() => {
    load();
  }, []);

  const del = async (t: Token) => {
    if (!confirm(`Убрать фишку «${t.name}» с карты?`)) return;
    await api.delete(`/admin/tokens/${t.id}`);
    load();
  };

  return (
    <div className="panel">
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Имя</th>
            <th>Комната</th>
            <th>Тип</th>
            <th>HP</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((t) => (
            <tr key={t.id}>
              <td>
                <span className="char-dot" style={{ background: t.color, display: "inline-block" }} /> {t.name}
              </td>
              <td>#{t.room_id}</td>
              <td>{t.is_npc ? "NPC" : "персонаж"}</td>
              <td>
                {t.hp}/{t.max_hp}
              </td>
              <td>
                <button className="small" onClick={() => del(t)}>
                  Убрать
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
