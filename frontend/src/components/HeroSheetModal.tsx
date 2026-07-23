// Просмотр свитка героя поверх игровой комнаты.
//
// Специально сделано модальным окном, а не переходом на /heroes: уход со страницы комнаты
// разрывает WebSocket и заново грузит карту с фишками. За партию свиток открывают десятки раз.
import { useEffect, useState } from "react";
import "../pages/heroes.css";
import { API_URL, api, errorMessage } from "../api/client";
import type { HeroSheet, Token } from "../api/types";
import { useAuth } from "../store/auth";
import HeroSheetEditor from "./HeroSheetEditor";

interface Props {
  heroId: number | null;
  // Фишка, по которой кликнули: показываем её данные, если свиток недоступен или его нет.
  token?: Token | null;
  onClose: () => void;
}

export default function HeroSheetModal({ heroId, token, onClose }: Props) {
  const user = useAuth((s) => s.user);
  const [hero, setHero] = useState<HeroSheet | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (heroId === null) {
      setHero(null);
      setError("");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    (async () => {
      try {
        const { data } = await api.get<HeroSheet>(`/heroes/${heroId}`);
        if (!cancelled) setHero(data);
      } catch (err) {
        // Чужой свиток смотреть нельзя — это не поломка, просто покажем данные фишки.
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [heroId]);

  // Закрытие по Esc — привычнее, чем искать крестик во время боя.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const canEdit = !!hero && (hero.owner_user_id === user?.id || user?.role === "admin");

  return (
    <div className="hero-modal-backdrop" onClick={onClose}>
      <div className="hero-modal" onClick={(e) => e.stopPropagation()}>
        <button className="hero-modal-close" onClick={onClose} title="Закрыть (Esc)">
          ✕
        </button>

        {loading && <p className="hs-muted" style={{ padding: 24 }}>Разворачиваем свиток…</p>}

        {!loading && hero && (
          <div className="hero-page">
            <HeroSheetEditor hero={hero} canEdit={canEdit} onCancel={onClose} onDone={onClose} />
          </div>
        )}

        {/* Свитка нет или он чужой — показываем то, что видно всем: саму фишку. */}
        {!loading && !hero && token && (
          <div className="hero-page">
            <div className="hero-scroll" style={{ maxWidth: 460 }}>
              <div className="hs-title">
                <h1>{token.name}</h1>
                <p>{token.is_npc ? "✧ NPC мастера ✧" : "✧ Фишка на карте ✧"}</p>
              </div>
              <div className="hs-section full">
                {token.avatar_url && (
                  <img
                    src={API_URL + token.avatar_url}
                    alt={token.name}
                    style={{ width: 120, height: 150, objectFit: "cover", borderRadius: 10, display: "block", margin: "0 auto 12px" }}
                  />
                )}
                <p style={{ textAlign: "center", fontSize: "1.1rem", margin: "0 0 8px" }}>
                  <b>Жизни:</b> {token.hp} / {token.max_hp}
                </p>
                {(token.effects || []).length > 0 && (
                  <p style={{ textAlign: "center", margin: 0 }}>
                    {token.effects.map((ef, i) => (
                      <span
                        key={i}
                        className="tag"
                        style={{ color: ef.type === "buff" ? "#3d6b28" : "#8b2f1c", borderColor: "currentColor", marginRight: 6 }}
                      >
                        {ef.type === "buff" ? "▲" : "▼"} {ef.name}
                      </span>
                    ))}
                  </p>
                )}
                <p className="hs-muted" style={{ textAlign: "center", marginBottom: 0, marginTop: 14 }}>
                  {error
                    ? "Полный свиток этого героя вам недоступен."
                    : "За этой фишкой не закреплён свиток героя."}
                </p>
              </div>
            </div>
          </div>
        )}

        {!loading && !hero && !token && <p className="hs-muted" style={{ padding: 24 }}>{error || "Свиток не найден."}</p>}
      </div>
    </div>
  );
}
