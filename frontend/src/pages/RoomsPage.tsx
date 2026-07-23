import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminEditOnce, api, errorMessage } from "../api/client";
import type { Room } from "../api/types";
import { hasActiveSubscription, useAuth } from "../store/auth";

export default function RoomsPage() {
  const user = useAuth((s) => s.user);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [newName, setNewName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const load = async () => {
    try {
      const { data } = await api.get<Room[]>("/rooms");
      setRooms(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.post<Room>("/rooms", { name: newName });
      // Создатель стал мастером — обновим профиль, чтобы роль подтянулась.
      await useAuth.getState().fetchMe();
      navigate(`/rooms/${data.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const joinRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.post<Room>("/rooms/join", { invite_code: joinCode });
      navigate(`/rooms/${data.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const deleteRoom = async (r: Room) => {
    // Чужую комнату админ удаляет только с отдельным предупреждением.
    const foreign = r.dm_id !== user?.id;
    const question = foreign
      ? `Это ЧУЖАЯ комната «${r.name}». Удалить её вместе с картой, фишками и историей бросков?`
      : `Удалить комнату «${r.name}»? Будут удалены её карта, фишки и история бросков.`;
    if (!confirm(question)) return;
    setError("");
    try {
      await api.delete(`/rooms/${r.id}`, foreign ? adminEditOnce : undefined);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const leaveRoom = async (r: Room) => {
    if (
      !confirm(
        `Выйти из комнаты «${r.name}»? Ваши фишки уберут с карты. Вернуться можно по коду ${r.invite_code}.`
      )
    )
      return;
    setError("");
    try {
      await api.post(`/rooms/${r.id}/leave`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const expires = user?.subscription_expires_at;

  return (
    <div>
      <h1>Игровые комнаты</h1>
      {expires && hasActiveSubscription(user) && (
        <div className="banner">
          Подписка активна до {new Date(expires).toLocaleDateString("ru-RU")}.
        </div>
      )}
      {error && <div className="error">{error}</div>}

      <div className="row" style={{ alignItems: "flex-start", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
        {user?.is_dm ? (
          <form className="panel" style={{ flex: 1, minWidth: 260 }} onSubmit={createRoom}>
            <h3>Создать комнату</h3>
            <p className="muted">Вы — мастер подземелий (DM), можете водить игру.</p>
            <div className="field">
              <input
                placeholder="Название кампании"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <button type="submit" disabled={!newName}>
              Создать
            </button>
          </form>
        ) : (
          <div className="panel" style={{ flex: 1, minWidth: 260 }}>
            <h3>Создать комнату</h3>
            <p className="muted">
              Создавать комнаты может только мастер подземелий (роль <b>DM</b>, Dungeon Master).
              Роль DM выдаёт администратор — обратитесь к нему. А пока вы можете присоединиться к комнате по коду.
            </p>
          </div>
        )}

        <form className="panel" style={{ flex: 1, minWidth: 260 }} onSubmit={joinRoom}>
          <h3>Присоединиться</h3>
          <p className="muted">Введите код-приглашение от мастера.</p>
          <div className="field">
            <input
              placeholder="Код комнаты"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            />
          </div>
          <button type="submit" className="secondary" disabled={!joinCode}>
            Войти в комнату
          </button>
        </form>
      </div>

      <h2>Мои комнаты</h2>
      {rooms.length === 0 ? (
        <p className="muted">Пока нет комнат. Создайте новую или присоединитесь по коду.</p>
      ) : (
        <div className="grid-cards">
          {rooms.map((r) => (
            <div className="card" key={r.id}>
              <h3>{r.name}</h3>
              <p className="muted">
                Код: <b>{r.invite_code}</b>
                {r.dm_id === user?.id && <span className="tag dm" style={{ marginLeft: 8 }}>вы мастер</span>}
              </p>
              <div className="row" style={{ gap: 6 }}>
                <button className="small" onClick={() => navigate(`/rooms/${r.id}`)}>
                  Открыть
                </button>
                {(r.dm_id === user?.id || user?.role === "admin") && (
                  <button className="secondary small" onClick={() => deleteRoom(r)}>
                    Удалить
                  </button>
                )}
                {/* Мастер выйти не может — комната без мастера бессмысленна, её удаляют. */}
                {r.dm_id !== user?.id && (
                  <button className="secondary small" onClick={() => leaveRoom(r)}>
                    Выйти
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
