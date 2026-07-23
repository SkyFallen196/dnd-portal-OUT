import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import type { CombatState, DiceRoll, RoomDetail, Token } from "../api/types";
import { useAuth } from "../store/auth";
import { useAdminEdit } from "../store/adminEdit";
import { useRoomSocket } from "../hooks/useRoomSocket";
import MapCanvas from "../components/MapCanvas";
import DiceRoller from "../components/DiceRoller";
import RollLog from "../components/RollLog";
import DMPanel from "../components/DMPanel";
import RoleTags from "../components/RoleTags";
import HeroSheetModal from "../components/HeroSheetModal";
import InitiativePanel from "../components/InitiativePanel";

export default function RoomPage() {
  const { roomId } = useParams();
  const id = Number(roomId);
  const user = useAuth((s) => s.user);
  const navigate = useNavigate();

  const [room, setRoom] = useState<RoomDetail | null>(null);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [rolls, setRolls] = useState<DiceRoll[]>([]);
  const [combat, setCombat] = useState<CombatState>({ round: 0, current_token_id: null, order: [] });
  // error — только фатальное (комнату не удалось загрузить), оно подменяет весь экран.
  // actionError — обычная неудача действия («сейчас не ваш ход»): показываем полоской,
  // не выкидывая игрока из комнаты посреди боя.
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  // Открытый свиток: либо по клику на фишку, либо кнопкой «Мой свиток» в шапке.
  const [sheet, setSheet] = useState<{ heroId: number | null; token: Token | null } | null>(null);

  const adminEdit = useAdminEdit((s) => s.enabled);
  const toggleAdminEdit = useAdminEdit((s) => s.toggle);
  const setAdminEdit = useAdminEdit((s) => s.set);
  // Мастер комнаты — всегда. Админ получает права мастера только с включённым режимом.
  const isOwnRoom = !!user && room?.dm_id === user.id;
  const isDM = isOwnRoom || (!!user && user.role === "admin" && adminEdit);
  // Тумблер показываем только там, где он что-то меняет: админу в ЧУЖОЙ комнате.
  // В своей комнате он мастер по определению, и режим ни на что не влияет.
  const showAdminToggle = !!user && user.role === "admin" && !!room && !isOwnRoom;

  // Уходя из комнаты, сбрасываем режим: по умолчанию админ всегда наблюдатель,
  // чтобы включённый когда-то тумблер не остался «висеть» незаметно.
  useEffect(() => {
    return () => setAdminEdit(false);
  }, [setAdminEdit]);

  const loadRoom = useCallback(async () => {
    const { data } = await api.get<RoomDetail>(`/rooms/${id}`);
    setRoom(data);
  }, [id]);

  const loadTokens = useCallback(async () => {
    const { data } = await api.get<Token[]>(`/rooms/${id}/tokens`);
    setTokens(data);
  }, [id]);

  useEffect(() => {
    (async () => {
      try {
        await loadRoom();
        await loadTokens();
        const { data } = await api.get<DiceRoll[]>(`/rooms/${id}/rolls`);
        setRolls(data);
        const c = await api.get<CombatState>(`/rooms/${id}/combat`);
        setCombat(c.data);
      } catch (err) {
        setError(errorMessage(err));
      }
    })();
  }, [id, loadRoom, loadTokens]);

  // Обработка событий реального времени.
  const onMessage = useCallback((msg: any) => {
    switch (msg.type) {
      case "token_moved":
        setTokens((prev) =>
          prev.map((t) => (t.id === msg.token.id ? { ...t, x: msg.token.x, y: msg.token.y } : t))
        );
        break;
      case "token_added":
        setTokens((prev) => (prev.some((t) => t.id === msg.token.id) ? prev : [...prev, msg.token]));
        break;
      case "token_updated":
        setTokens((prev) => prev.map((t) => (t.id === msg.token.id ? msg.token : t)));
        break;
      case "token_removed":
        setTokens((prev) => prev.filter((t) => t.id !== msg.token_id));
        break;
      case "dice_rolled":
        setRolls((prev) => [...prev, msg.roll]);
        break;
      case "combat_updated":
        // Состояние боя приходит целиком — просто заменяем.
        setCombat(msg.combat);
        break;
      case "map_changed":
        // Мастер сменил карту — подменяем её у всех, кто сидит в комнате.
        setRoom((prev) =>
          prev ? { ...prev, active_map: msg.map, active_map_id: msg.map?.id ?? null } : prev
        );
        break;
      case "room_deleted":
        alert("Комната была удалена мастером.");
        navigate("/rooms");
        break;
    }
  }, [navigate]);

  const { sendMove } = useRoomSocket(id, onMessage);

  const canMove = (tk: Token) => isDM || tk.owner_user_id === user?.id;

  // Во время перетаскивания — оптимистично двигаем локально и шлём по WebSocket.
  const handleMove = (tokenId: number, x: number, y: number) => {
    setTokens((prev) => prev.map((t) => (t.id === tokenId ? { ...t, x, y } : t)));
    sendMove(tokenId, x, y);
  };

  // Клик по фишке открывает свиток героя, из которого её выставили.
  // Если свитка нет (NPC) или он чужой — модалка покажет данные самой фишки.
  const openTokenSheet = (tk: Token) => setSheet({ heroId: tk.hero_sheet_id, token: tk });

  // «Мой свиток»: берём тот, что закреплён за моей фишкой в этой комнате,
  // иначе — первый из моих свитков.
  const openMySheet = async () => {
    const mine = tokens.find((t) => t.owner_user_id === user?.id && t.hero_sheet_id);
    if (mine) {
      setSheet({ heroId: mine.hero_sheet_id, token: mine });
      return;
    }
    try {
      const { data } = await api.get<{ id: number }[]>("/heroes");
      if (data.length === 0) {
        setActionError("У вас пока нет свитка героя — создайте его на странице «Свиток героя».");
        return;
      }
      setSheet({ heroId: data[0].id, token: null });
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  const handleRoll = async (formula: string, rollType: string) => {
    try {
      // Результат прилетит всем (и нам) через WebSocket-событие dice_rolled.
      await api.post(`/rooms/${id}/roll`, { formula, roll_type: rollType });
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  if (error) {
    return (
      <div className="center-screen">
        <div className="panel">
          <div className="error">{error}</div>
          <button onClick={() => navigate("/rooms")}>← К комнатам</button>
        </div>
      </div>
    );
  }
  if (!room) return <div className="center-screen">Загрузка комнаты…</div>;

  return (
    <div>
      <nav className="nav">
        <button className="secondary small" onClick={() => navigate("/rooms")}>
          ← Комнаты
        </button>
        <span className="brand" style={{ fontSize: "1.1rem" }}>
          {room.name}
        </span>
        <span className="badge">
          код приглашения: <b>{room.invite_code}</b>
        </span>
        <button
          className="secondary small"
          onClick={openMySheet}
          title="Открыть свой свиток, не выходя из комнаты"
        >
          📜 Мой свиток
        </button>
        {showAdminToggle && (
          <button
            className={adminEdit ? "small" : "secondary small"}
            onClick={toggleAdminEdit}
            title={
              adminEdit
                ? "Вы правите чужую игру как мастер. Выключите, чтобы случайно ничего не задеть."
                : "Вы в чужой комнате как наблюдатель. Включите, чтобы получить права мастера."
            }
          >
            {adminEdit ? "✏ Режим редактирования: ВКЛ" : "👁 Наблюдатель — включить правку"}
          </button>
        )}
        <span className="spacer" />
        <span className="badge">
          {user?.username} <RoleTags user={user} />
        </span>
      </nav>

      {actionError && (
        <div className="error" style={{ margin: "8px 12px", cursor: "pointer" }} onClick={() => setActionError("")}>
          {actionError} <span className="muted">(нажмите, чтобы скрыть)</span>
        </div>
      )}

      <div className="room-layout">
        <div className="map-area">
          <MapCanvas
            mapUrl={room.active_map?.file_path ?? null}
            tokens={tokens}
            canMove={canMove}
            onMove={handleMove}
            onMoveEnd={(tokenId, x, y) => sendMove(tokenId, x, y)}
            onSelect={openTokenSheet}
            activeTokenId={combat.current_token_id}
          />
        </div>

        <div className="sidebar">
          <div className="sidebar-section">
            <InitiativePanel
              roomId={id}
              combat={combat}
              isDM={isDM}
              currentUserId={user?.id}
              onError={setActionError}
            />
          </div>
          <div className="sidebar-section">
            <DiceRoller onRoll={handleRoll} />
          </div>
          <div className="sidebar-section">
            <RollLog rolls={rolls} />
          </div>
          {isDM && (
            <DMPanel
              room={room}
              tokens={tokens}
              onReload={async () => {
                await loadRoom();
                await loadTokens();
              }}
            />
          )}
        </div>
      </div>

      {sheet && (
        <HeroSheetModal heroId={sheet.heroId} token={sheet.token} onClose={() => setSheet(null)} />
      )}
    </div>
  );
}
