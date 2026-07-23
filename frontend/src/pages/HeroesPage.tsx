import { useEffect, useState } from "react";
import "./heroes.css";
import { API_URL, api, errorMessage } from "../api/client";
import type { HeroSheet, HeroSummary, Room } from "../api/types";
import { hasActiveSubscription, useAuth } from "../store/auth";
import HeroSheetEditor from "../components/HeroSheetEditor";

// ---------- Страница со списком свитков ----------
export default function HeroesPage() {
  const user = useAuth((s) => s.user);
  const isStaff = !!user?.is_dm || user?.role === "admin";
  // Свиток можно завести и без подписки, а вот выставить героя на карту — уже игровое
  // действие: сервер потребует активную подписку, поэтому предупреждаем заранее.
  const canPlay = hasActiveSubscription(user);

  const [heroes, setHeroes] = useState<HeroSheet[]>([]);
  const [all, setAll] = useState<HeroSummary[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [open, setOpen] = useState<{ hero: HeroSheet | null; canEdit: boolean } | null>(null);
  // Выставление героя на карту
  const [rooms, setRooms] = useState<Room[]>([]);
  const [placingFor, setPlacingFor] = useState<number | null>(null);
  const [placeRoomId, setPlaceRoomId] = useState("");
  const [placing, setPlacing] = useState(false);

  const load = async () => {
    setError("");
    try {
      const { data } = await api.get<HeroSheet[]>("/heroes");
      setHeroes(data);
      if (isStaff) {
        const r = await api.get<HeroSummary[]>("/heroes/all");
        setAll(r.data);
      }
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openHero = async (id: number) => {
    try {
      const { data } = await api.get<HeroSheet>(`/heroes/${id}`);
      const canEdit = data.owner_user_id === user?.id || user?.role === "admin";
      setOpen({ hero: data, canEdit });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  // Открыть выбор комнаты для конкретного героя (список комнат подгружаем один раз).
  const startPlacing = async (heroId: number) => {
    setError("");
    setNotice("");
    setPlacingFor(heroId);
    if (rooms.length === 0) {
      try {
        const { data } = await api.get<Room[]>("/rooms");
        setRooms(data);
        if (data.length > 0) setPlaceRoomId(String(data[0].id));
      } catch (err) {
        setError(errorMessage(err));
      }
    }
  };

  const placeHero = async (h: HeroSheet) => {
    if (!placeRoomId) return;
    setError("");
    setPlacing(true);
    try {
      await api.post(`/heroes/${h.id}/place`, { room_id: Number(placeRoomId) });
      const room = rooms.find((r) => String(r.id) === placeRoomId);
      setNotice(`«${h.name}» выставлен на карту комнаты «${room?.name ?? placeRoomId}».`);
      setPlacingFor(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPlacing(false);
    }
  };

  const deleteHero = async (h: HeroSheet) => {
    if (!confirm(`Сжечь свиток «${h.name}»? Это навсегда.`)) return;
    try {
      await api.delete(`/heroes/${h.id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (open) {
    return (
      <div className="hero-page">
        <HeroSheetEditor
          hero={open.hero}
          canEdit={open.canEdit}
          onCancel={() => setOpen(null)}
          onDone={() => {
            setOpen(null);
            load();
          }}
        />
      </div>
    );
  }

  const othersHeroes = all.filter((h) => h.owner_user_id !== user?.id);

  return (
    <div className="hero-page">
      <div className="hero-scroll">
        <div className="hs-title">
          <h1>Мои герои</h1>
          <p>✧ Свитки, что хранят твою судьбу ✧</p>
        </div>
        {error && <div className="hs-error">{error}</div>}
        {notice && <div className="hs-notice">{notice}</div>}

        <div className="hs-toolbar">
          <button className="hs-btn" onClick={() => setOpen({ hero: null, canEdit: true })}>
            ✦ Новый свиток
          </button>
        </div>

        {heroes.length === 0 ? (
          <p className="hs-muted">Пока ни одного свитка. Заведи первого героя!</p>
        ) : (
          <div className="hs-cards">
            {heroes.map((h) => (
              <div key={h.id}>
                <div className="hs-card">
                  <div className={`hs-card-portrait hs-crop-${h.crop_position}`}>
                    {h.portrait_url ? <img src={API_URL + h.portrait_url} alt={h.name} /> : <span>🧝</span>}
                  </div>
                  <div className="hs-card-body">
                    <div className="hs-card-name">{h.name}</div>
                    <div className="hs-card-sub">{h.race || "без расы"}</div>
                  </div>
                  <div className="hs-card-actions">
                    <button className="hs-btn small" onClick={() => openHero(h.id)}>Открыть</button>
                    {canPlay ? (
                      <button className="hs-btn small" onClick={() => startPlacing(h.id)}>На карту</button>
                    ) : (
                      <button
                        className="hs-btn small ghost"
                        title="Для игры нужна активная подписка"
                        onClick={() =>
                          setError("Чтобы выставить героя на карту, нужна активная подписка — активируйте код доступа.")
                        }
                      >
                        На карту 🔒
                      </button>
                    )}
                    <button className="hs-btn small danger" onClick={() => deleteHero(h)}>Сжечь</button>
                  </div>
                </div>

                {placingFor === h.id && (
                  <div className="hs-place">
                    {rooms.length === 0 ? (
                      <p className="hs-muted">
                        Нет доступных комнат. Сначала присоединитесь к комнате по коду мастера.
                      </p>
                    ) : (
                      <>
                        <div className="hs-field">
                          <label>В какую комнату выставить</label>
                          <select value={placeRoomId} onChange={(e) => setPlaceRoomId(e.target.value)}>
                            {rooms.map((r) => (
                              <option key={r.id} value={r.id}>{r.name}</option>
                            ))}
                          </select>
                        </div>
                        <div className="hs-place-actions">
                          <button className="hs-btn small ghost" onClick={() => setPlacingFor(null)}>
                            Отмена
                          </button>
                          <button className="hs-btn small" disabled={placing} onClick={() => placeHero(h)}>
                            {placing ? "Выставляем…" : "Выставить"}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {isStaff && othersHeroes.length > 0 && (
        <>
          <h2 className="hs-subheading">Герои игроков (просмотр)</h2>
          <div className="hero-scroll">
            <div className="hs-cards">
              {othersHeroes.map((h) => (
                <div className="hs-card" key={h.id}>
                  <div className="hs-card-portrait">
                    {h.portrait_url ? <img src={API_URL + h.portrait_url} alt={h.name} /> : <span>🧝</span>}
                  </div>
                  <div className="hs-card-body">
                    <div className="hs-card-name">{h.name}</div>
                    <div className="hs-card-sub">{h.race || "без расы"} · {h.owner_username}</div>
                  </div>
                  <div className="hs-card-actions">
                    <button className="hs-btn small" onClick={() => openHero(h.id)}>Открыть</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
