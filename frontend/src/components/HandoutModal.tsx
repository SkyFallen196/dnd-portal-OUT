// Просмотр раздаточного материала поверх игровой комнаты.
//
// Как и свиток героя, сделано модальным окном: уход со страницы комнаты разрывает
// WebSocket и заново грузит карту с фишками.
import { useEffect } from "react";
import { API_URL } from "../api/client";
import type { Handout } from "../api/types";

interface Props {
  handout: Handout;
  onClose: () => void;
}

export default function HandoutModal({ handout, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="handout-backdrop" onClick={onClose}>
      <div className="handout-modal panel" onClick={(e) => e.stopPropagation()}>
        <button className="handout-close" onClick={onClose} title="Закрыть (Esc)">
          ✕
        </button>

        <h2 style={{ marginRight: 32 }}>{handout.title}</h2>
        {!handout.is_public && (
          <p className="muted" style={{ marginTop: -8 }}>
            🙈 Партия этого пока не видит — материал открыт только вам.
          </p>
        )}

        {handout.image_url && (
          <img className="handout-image" src={API_URL + handout.image_url} alt={handout.title} />
        )}

        {/* pre-wrap: текст сохраняет абзацы и переносы так, как их набрал мастер. */}
        {handout.body && <div className="handout-body">{handout.body}</div>}
        {!handout.body && !handout.image_url && <p className="muted">Материал пока пуст.</p>}
      </div>
    </div>
  );
}
