import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { API_URL, api, errorMessage } from "../api/client";
import type { MapImage, Member, RoomDetail, Token } from "../api/types";

interface Props {
  room: RoomDetail;
  tokens: Token[];
  onReload: () => void;
}

const COLORS = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#f39c12", "#16a085", "#d35400", "#7f8c8d"];

// Те же границы размера фишки, что и на сервере (schemas.py: MIN_TOKEN_SIZE/MAX_TOKEN_SIZE).
const MIN_SIZE = 0.4;
const MAX_SIZE = 5;

// Подпись строки в редакторе фишки. Ширина — по самому длинному слову («Размер»),
// иначе оно вылезает за колонку и его накрывает соседняя кнопка. flexShrink: 0 —
// чтобы подпись не сжимало, когда в строке много кнопок.
const ROW_LABEL: CSSProperties = { width: 54, flexShrink: 0 };

// Панель мастера: карта, фишки на ней, управление участниками.
export default function DMPanel({ room, tokens, onReload }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [ownerId, setOwnerId] = useState<string>("");
  const [hp, setHp] = useState(10);
  const [isNpc, setIsNpc] = useState(false);
  const [isHidden, setIsHidden] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [effName, setEffName] = useState("");
  const [effType, setEffType] = useState<"buff" | "debuff">("buff");
  const [maps, setMaps] = useState<MapImage[]>([]);

  // Список загруженных карт: между ними можно переключаться, не загружая заново.
  const loadMaps = useCallback(async () => {
    try {
      const { data } = await api.get<MapImage[]>(`/rooms/${room.id}/maps`);
      setMaps(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [room.id]);

  useEffect(() => {
    loadMaps();
  }, [loadMaps]);

  const activateMap = async (m: MapImage) => {
    setError("");
    try {
      // Карта сменится у всех сразу — сервер разошлёт событие map_changed.
      await api.post(`/rooms/${room.id}/maps/${m.id}/activate`);
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const deleteMap = async (m: MapImage) => {
    if (!confirm(`Удалить карту «${m.filename}»? Файл будет стёрт с диска.`)) return;
    setError("");
    try {
      await api.delete(`/rooms/${room.id}/maps/${m.id}`);
      await loadMaps();
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const uploadMap = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post(`/rooms/${room.id}/map`, form);
      await loadMaps();
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const createToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.post(`/rooms/${room.id}/tokens`, {
        name,
        color,
        hp,
        max_hp: hp,
        is_npc: isNpc,
        hidden: isHidden,
        owner_user_id: ownerId ? Number(ownerId) : null,
        x: 120,
        y: 120,
      });
      setName("");
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const deleteToken = async (id: number) => {
    if (!confirm("Убрать фишку с карты?")) return;
    try {
      await api.delete(`/rooms/${room.id}/tokens/${id}`);
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const uploadAvatar = async (tokenId: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post(`/rooms/${room.id}/tokens/${tokenId}/avatar`, form);
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      e.target.value = "";
    }
  };

  // Общая правка фишки (обновление прилетит всем через WebSocket).
  const patchToken = async (t: Token, data: Record<string, unknown>) => {
    setError("");
    try {
      await api.patch(`/rooms/${room.id}/tokens/${t.id}`, data);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  // Слои: «наверх» — стать выше всех, «вниз» — уйти под всех. Абсолютные значения z
  // не важны, важен только порядок, поэтому просто выходим за текущие границы.
  const zTop = tokens.reduce((m, t) => Math.max(m, t.z || 0), 0);
  const zBottom = tokens.reduce((m, t) => Math.min(m, t.z || 0), 0);

  const setGrid = async (value: number) => {
    setError("");
    try {
      // Сетка сменится у всех сразу — сервер разошлёт событие room_updated.
      await api.patch(`/rooms/${room.id}`, { grid_size: Math.max(0, Math.min(500, value)) });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const adjustHp = (t: Token, delta: number) =>
    patchToken(t, { hp: Math.max(0, Math.min(t.max_hp, t.hp + delta)) });
  // Точное значение HP: вписать число вручную вместо шагов ±1/±5.
  // Пустое поле игнорируем; больше максимума сервер всё равно обрежет.
  const setHpExact = (t: Token, val: number) => {
    if (Number.isNaN(val)) return;
    patchToken(t, { hp: Math.max(0, Math.min(t.max_hp, val)) });
  };
  const setMaxHp = (t: Token, val: number) => {
    if (!val || val < 1) return;
    patchToken(t, { max_hp: val, hp: Math.min(t.hp, val) });
  };
  const adjustSize = (t: Token, delta: number) =>
    patchToken(t, { size: Math.max(MIN_SIZE, Math.min(MAX_SIZE, +((t.size || 1) + delta).toFixed(2))) });
  const addEffect = (t: Token) => {
    const name = effName.trim();
    if (!name) return;
    patchToken(t, { effects: [...(t.effects || []), { name, type: effType }] });
    setEffName("");
  };
  const removeEffect = (t: Token, idx: number) =>
    patchToken(t, { effects: (t.effects || []).filter((_, i) => i !== idx) });

  const removeMember = async (m: Member) => {
    if (!confirm(`Удалить ${m.username} из комнаты?`)) return;
    try {
      await api.delete(`/rooms/${room.id}/members/${m.user_id}`);
      onReload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="sidebar-section">
      <h3>🛡 Панель мастера</h3>
      {error && <div className="error">{error}</div>}

      <div className="field">
        <label>Карта (изображение)</label>
        <input ref={fileRef} type="file" accept="image/*" onChange={uploadMap} disabled={uploading} />
        {uploading && <p className="muted">Загрузка…</p>}
      </div>

      {maps.length > 0 && (
        <div className="field">
          <label>Загруженные карты ({maps.length})</label>
          {maps.map((m) => {
            const active = m.id === room.active_map_id;
            return (
              <div className="char-item" key={m.id}>
                <img
                  src={API_URL + m.file_path}
                  alt={m.filename}
                  style={{
                    width: 40,
                    height: 30,
                    objectFit: "cover",
                    borderRadius: 4,
                    border: `2px solid ${active ? "var(--gold)" : "var(--border)"}`,
                  }}
                />
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {m.filename}
                  {active && <span className="tag dm" style={{ marginLeft: 6 }}>активна</span>}
                </span>
                {!active && (
                  <button className="secondary small" title="Показать эту карту всем" onClick={() => activateMap(m)}>
                    ▶
                  </button>
                )}
                <button className="secondary small" title="Удалить карту" onClick={() => deleteMap(m)}>
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div className="field">
        <label>Сетка (одна клетка = 5 футов)</label>
        <div className="row" style={{ gap: 6 }}>
          <input
            type="number"
            min={0}
            max={500}
            // key сбрасывает поле, если сетку поменяли из другого места.
            key={room.grid_size}
            defaultValue={room.grid_size}
            style={{ width: 90 }}
            // Enter снимает фокус — срабатывает тот же onBlur, значение уходит одним запросом.
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
            onBlur={(e) => setGrid(Number(e.target.value))}
          />
          <button className="secondary small" disabled={!room.grid_size} onClick={() => setGrid(0)}>
            Выключить
          </button>
        </div>
        <p className="muted" style={{ margin: "4px 0 0" }}>
          Сторона клетки в пикселях карты; 0 — сетки нет.
        </p>
      </div>

      <form onSubmit={createToken} style={{ marginTop: 8 }}>
        <label>Новая фишка (персонаж или NPC)</label>
        <div className="field">
          <input placeholder="Имя" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Цвет фишки</label>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            {COLORS.map((c) => (
              <div
                key={c}
                onClick={() => setColor(c)}
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: c,
                  cursor: "pointer",
                  border: color === c ? "3px solid #fff" : "2px solid #555",
                }}
              />
            ))}
          </div>
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>HP</label>
            <input type="number" value={hp} min={1} onChange={(e) => setHp(Number(e.target.value))} />
          </div>
          <div className="field" style={{ flex: 2 }}>
            <label>Владелец</label>
            <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
              <option value="">— без владельца —</option>
              {room.members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.username}
                </option>
              ))}
            </select>
          </div>
        </div>
        <label className="row" style={{ gap: 6, marginBottom: 8 }}>
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={isNpc}
            onChange={(e) => setIsNpc(e.target.checked)}
          />
          <span>Это NPC</span>
        </label>
        <label className="row" style={{ gap: 6, marginBottom: 8 }} title="Игроки её не увидят, пока не покажете">
          <input
            type="checkbox"
            style={{ width: "auto" }}
            checked={isHidden}
            onChange={(e) => setIsHidden(e.target.checked)}
          />
          <span>Скрыть от игроков</span>
        </label>
        <button type="submit" disabled={!name}>
          Добавить на карту
        </button>
      </form>

      <div style={{ marginTop: 16 }}>
        <label>Фишки на карте</label>
        {tokens.map((t) => (
          <div key={t.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 4, marginBottom: 4 }}>
            <div className="char-item">
              {t.avatar_url ? (
                <img
                  src={API_URL + t.avatar_url}
                  alt={t.name}
                  className="char-dot"
                  style={{ objectFit: "cover", borderColor: t.color }}
                />
              ) : (
                <span className="char-dot" style={{ background: t.color }} />
              )}
              <span style={{ flex: 1 }}>
                {t.name} <span className="muted">{t.hp}/{t.max_hp}</span>
                {t.hidden && <span className="tag" style={{ marginLeft: 6, opacity: 0.8 }}>скрыта</span>}
              </span>
              <button
                className="secondary small"
                title={t.hidden ? "Скрыта от игроков — показать" : "Видна игрокам — скрыть"}
                onClick={() => patchToken(t, { hidden: !t.hidden })}
              >
                {t.hidden ? "🙈" : "👁"}
              </button>
              <button
                className="secondary small"
                title="Изменить HP, размер, эффекты"
                onClick={() => setEditingId(editingId === t.id ? null : t.id)}
              >
                ⚙
              </button>
              <label
                title="Загрузить аватар"
                style={{
                  cursor: "pointer",
                  padding: "5px 8px",
                  fontSize: "0.85rem",
                  background: "var(--bg-panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  margin: 0,
                }}
              >
                🖼
                <input type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => uploadAvatar(t.id, e)} />
              </label>
              <button className="secondary small" title="Убрать с карты" onClick={() => deleteToken(t.id)}>
                ✕
              </button>
            </div>

            {editingId === t.id && (
              <div style={{ padding: "8px 4px 4px" }}>
                {/* HP */}
                <div className="row" style={{ gap: 4, marginBottom: 6, alignItems: "center" }}>
                  <span className="muted" style={ROW_LABEL}>HP</span>
                  <button className="secondary small" onClick={() => adjustHp(t, -5)}>−5</button>
                  <button className="secondary small" onClick={() => adjustHp(t, -1)}>−1</button>
                  {/* Клик по числу — вписать точное HP. key сбрасывает поле, когда HP
                      меняют кнопками ±: тогда defaultValue берёт свежее значение. */}
                  <input
                    type="number"
                    min={0}
                    max={t.max_hp}
                    key={t.hp}
                    defaultValue={t.hp}
                    title="Впишите точное значение"
                    style={{ width: 56, textAlign: "center", padding: "3px 4px", fontWeight: "bold" }}
                    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                    onBlur={(e) => setHpExact(t, Number(e.target.value))}
                  />
                  <button className="secondary small" onClick={() => adjustHp(t, 1)}>+1</button>
                  <button className="secondary small" onClick={() => adjustHp(t, 5)}>+5</button>
                </div>
                <div className="row" style={{ gap: 6, marginBottom: 6, alignItems: "center" }}>
                  <span className="muted" style={ROW_LABEL}>Max</span>
                  <input
                    type="number"
                    min={1}
                    defaultValue={t.max_hp}
                    style={{ width: 80 }}
                    onBlur={(e) => setMaxHp(t, Number(e.target.value))}
                  />
                </div>
                {/* Размер */}
                <div className="row" style={{ gap: 6, marginBottom: 8, alignItems: "center" }}>
                  <span className="muted" style={ROW_LABEL}>Размер</span>
                  <button className="secondary small" onClick={() => adjustSize(t, -0.25)}>−</button>
                  <b style={{ minWidth: 44, textAlign: "center" }}>×{(t.size || 1).toFixed(2)}</b>
                  <button className="secondary small" onClick={() => adjustSize(t, 0.25)}>+</button>
                </div>
                {/* Слой: чтобы фишку не накрывала соседняя в толкучке */}
                <div className="row" style={{ gap: 6, marginBottom: 8, alignItems: "center" }}>
                  <span className="muted" style={ROW_LABEL}>Слой</span>
                  <button
                    className="secondary small"
                    title="Поднять над остальными фишками"
                    onClick={() => patchToken(t, { z: zTop + 1 })}
                  >
                    ⬆ наверх
                  </button>
                  <button
                    className="secondary small"
                    title="Убрать под остальные фишки"
                    onClick={() => patchToken(t, { z: zBottom - 1 })}
                  >
                    ⬇ вниз
                  </button>
                </div>
                {/* Эффекты */}
                <div>
                  <span className="muted">Баффы / дебаффы</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4, margin: "4px 0" }}>
                    {(t.effects || []).length === 0 && <span className="muted">нет</span>}
                    {(t.effects || []).map((ef, i) => (
                      <span
                        key={i}
                        className="tag"
                        style={{ color: ef.type === "buff" ? "var(--green)" : "#ff8a80", borderColor: "currentColor" }}
                      >
                        {ef.type === "buff" ? "▲" : "▼"} {ef.name}
                        <span onClick={() => removeEffect(t, i)} style={{ cursor: "pointer", marginLeft: 4 }}>✕</span>
                      </span>
                    ))}
                  </div>
                  <div className="row" style={{ gap: 4 }}>
                    <input
                      placeholder="Напр. Отравлен"
                      value={effName}
                      onChange={(e) => setEffName(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && addEffect(t)}
                    />
                    <select value={effType} onChange={(e) => setEffType(e.target.value as "buff" | "debuff")} style={{ width: 100 }}>
                      <option value="buff">Бафф</option>
                      <option value="debuff">Дебафф</option>
                    </select>
                    <button className="small" disabled={!effName.trim()} onClick={() => addEffect(t)}>+</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        <label>Участники ({room.members.length})</label>
        {room.members.map((m) => (
          <div className="char-item" key={m.user_id}>
            <span style={{ flex: 1 }}>
              {m.username}{" "}
              {m.user_id === room.dm_id ? (
                <span className="tag dm">мастер</span>
              ) : (
                <span className="tag player">игрок</span>
              )}
            </span>
            {m.user_id !== room.dm_id && (
              <button className="secondary small" onClick={() => removeMember(m)}>
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
