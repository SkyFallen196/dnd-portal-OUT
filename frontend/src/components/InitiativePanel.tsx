import { api, errorMessage } from "../api/client";
import type { CombatState } from "../api/types";

interface Props {
  roomId: number;
  combat: CombatState;
  isDM: boolean;
  currentUserId?: number;
  onError: (msg: string) => void;
}

// Порядок ходов в бою. Состояние приходит с сервера и обновляется у всех
// через WebSocket-событие combat_updated, поэтому локально ничего не храним.
export default function InitiativePanel({ roomId, combat, isDM, currentUserId, onError }: Props) {
  const inFight = combat.round > 0;

  const call = async (path: string, method: "post" | "patch" = "post", body?: unknown) => {
    try {
      await api[method](`/rooms/${roomId}/combat${path}`, body);
    } catch (err) {
      onError(errorMessage(err));
    }
  };

  const start = () => call("/start");
  const next = () => call("/next");
  const end = () => {
    if (!confirm("Завершить бой? Порядок ходов будет сброшен.")) return;
    call("/end");
  };
  const setInitiative = (tokenId: number, value: string) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return;
    call(`/tokens/${tokenId}`, "patch", { initiative: n });
  };
  const removeFromFight = (tokenId: number) =>
    call(`/tokens/${tokenId}`, "patch", { initiative: null });

  // Свой ход можно завершить самому — не дёргая мастера.
  const currentIsMine =
    !!currentUserId &&
    combat.order.some((c) => c.token_id === combat.current_token_id && c.owner_user_id === currentUserId);
  const currentName = combat.order.find((c) => c.token_id === combat.current_token_id)?.name;

  return (
    <div>
      <h3>
        ⚔ Порядок ходов
        {inFight && <span className="badge" style={{ marginLeft: 8 }}>раунд {combat.round}</span>}
      </h3>

      {!inFight && (
        <p className="muted">
          Бой не идёт.
          {isDM
            ? " Начните бой — портал бросит d20 инициативы всем фишкам на карте."
            : " Мастер начнёт его, когда придёт время."}
        </p>
      )}

      {inFight && (
        <div className="init-list">
          {combat.order.map((c) => {
            const active = c.token_id === combat.current_token_id;
            return (
              <div key={c.token_id} className={active ? "init-row active" : "init-row"}>
                <span className="init-num">{active ? "▶" : ""}</span>
                <span className="char-dot" style={{ background: c.color, flexShrink: 0 }} />
                <span className="init-name">
                  {c.name}
                  {c.is_npc && <span className="muted"> · NPC</span>}
                </span>
                <span className="muted" style={{ whiteSpace: "nowrap" }}>
                  {c.hp}/{c.max_hp}
                </span>
                {isDM ? (
                  <>
                    <input
                      type="number"
                      className="init-input"
                      defaultValue={c.initiative}
                      title="Инициатива"
                      onBlur={(e) => setInitiative(c.token_id, e.target.value)}
                    />
                    <button
                      className="secondary small"
                      title="Убрать из боя"
                      onClick={() => removeFromFight(c.token_id)}
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <b className="init-value">{c.initiative}</b>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="row" style={{ gap: 6, marginTop: 10, flexWrap: "wrap" }}>
        {isDM && !inFight && <button onClick={start}>Начать бой</button>}
        {inFight && (isDM || currentIsMine) && (
          <button onClick={next}>{isDM ? "Следующий ход" : "Завершить свой ход"}</button>
        )}
        {isDM && inFight && (
          <button className="secondary" onClick={end}>
            Завершить бой
          </button>
        )}
      </div>

      {inFight && !isDM && !currentIsMine && (
        <p className="muted" style={{ marginBottom: 0, marginTop: 8 }}>
          {/* Скрытых фишек в порядке ходов у игрока нет вовсе: если сейчас ходит такая,
              сервер присылает current_token_id = null. Честно говорим, что ход не наш. */}
          {currentName ? (
            <>Сейчас ходит <b>{currentName}</b>.</>
          ) : (
            <>Сейчас ходит кто-то, кого вы пока не видите.</>
          )}
        </p>
      )}
    </div>
  );
}
