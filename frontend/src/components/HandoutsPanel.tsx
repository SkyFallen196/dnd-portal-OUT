// Заметки и раздаточные материалы комнаты.
//
// Мастер видит все, игрок — только опубликованные (сервер остальные ему и не присылает).
// Публикация и снятие с публикации прилетают всем через WebSocket, так что открытый
// материал появляется у партии сразу, без перезагрузки страницы.
import { useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Handout } from "../api/types";

interface Props {
  roomId: number;
  handouts: Handout[];
  isDM: boolean;
  onOpen: (h: Handout) => void;
}

export default function HandoutsPanel({ roomId, handouts, isDM, onOpen }: Props) {
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const resetForm = () => {
    setTitle("");
    setBody("");
    setAdding(false);
    setEditingId(null);
  };

  const create = async () => {
    if (!title.trim()) return;
    setError("");
    try {
      await api.post(`/rooms/${roomId}/handouts`, { title: title.trim(), body, is_public: false });
      resetForm();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const saveEdit = async (h: Handout) => {
    if (!title.trim()) return;
    setError("");
    try {
      await api.patch(`/rooms/${roomId}/handouts/${h.id}`, { title: title.trim(), body });
      resetForm();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const togglePublic = async (h: Handout) => {
    setError("");
    try {
      await api.patch(`/rooms/${roomId}/handouts/${h.id}`, { is_public: !h.is_public });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (h: Handout) => {
    if (!confirm(`Удалить материал «${h.title}»?`)) return;
    setError("");
    try {
      await api.delete(`/rooms/${roomId}/handouts/${h.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const uploadImage = async (h: Handout, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post(`/rooms/${roomId}/handouts/${h.id}/image`, form);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      e.target.value = "";
    }
  };

  const startEdit = (h: Handout) => {
    setAdding(false);
    setEditingId(h.id);
    setTitle(h.title);
    setBody(h.body);
  };

  return (
    <div>
      <h3>📖 Материалы</h3>
      {error && <div className="error">{error}</div>}

      {handouts.length === 0 && (
        <p className="muted">
          {isDM
            ? "Пока пусто. Здесь удобно держать описания, письма и портреты NPC — и открывать их партии в нужный момент."
            : "Мастер пока ничего не открыл."}
        </p>
      )}

      {handouts.map((h) => (
        <div key={h.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 4, marginBottom: 4 }}>
          <div className="char-item">
            <span
              className="handout-title"
              onClick={() => onOpen(h)}
              title="Открыть материал"
            >
              {h.image_url ? "🖼" : "📄"} {h.title}
            </span>
            {isDM && (
              <>
                <button
                  className="secondary small"
                  title={h.is_public ? "Партия его видит — спрятать" : "Скрыт от партии — показать"}
                  onClick={() => togglePublic(h)}
                >
                  {h.is_public ? "👁" : "🙈"}
                </button>
                <button className="secondary small" title="Изменить текст" onClick={() => startEdit(h)}>
                  ✎
                </button>
                <label className="file-button" title="Прикрепить картинку">
                  🖼
                  <input type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => uploadImage(h, e)} />
                </label>
                <button className="secondary small" title="Удалить материал" onClick={() => remove(h)}>
                  ✕
                </button>
              </>
            )}
          </div>

          {editingId === h.id && (
            <div style={{ padding: "6px 4px" }}>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Заголовок" />
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Текст материала"
                rows={5}
                style={{ marginTop: 6 }}
              />
              <div className="row" style={{ gap: 6, marginTop: 6 }}>
                <button className="small" onClick={() => saveEdit(h)} disabled={!title.trim()}>
                  Сохранить
                </button>
                <button className="secondary small" onClick={resetForm}>
                  Отмена
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {isDM && !adding && editingId === null && (
        <button className="secondary small" style={{ marginTop: 8 }} onClick={() => setAdding(true)}>
          + Новый материал
        </button>
      )}

      {isDM && adding && (
        <div style={{ marginTop: 8 }}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Заголовок" autoFocus />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Текст материала (можно оставить пустым и прикрепить картинку)"
            rows={5}
            style={{ marginTop: 6 }}
          />
          <p className="muted" style={{ margin: "6px 0" }}>
            Материал создаётся скрытым — откроете партии кнопкой 🙈, когда придёт время.
          </p>
          <div className="row" style={{ gap: 6 }}>
            <button className="small" onClick={create} disabled={!title.trim()}>
              Создать
            </button>
            <button className="secondary small" onClick={resetForm}>
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
