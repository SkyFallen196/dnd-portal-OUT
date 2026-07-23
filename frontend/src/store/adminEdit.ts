// «Режим редактирования» админа.
//
// По умолчанию админ в чужой комнате — наблюдатель (модератор). Чтобы менять игру,
// он должен явно включить тумблер. Флаг уходит на сервер заголовком X-Admin-Edit,
// то есть это не просто спрятанные кнопки — сервер тоже его проверяет.
import { create } from "zustand";

const KEY = "dnd_admin_edit";

interface AdminEditState {
  enabled: boolean;
  toggle: () => void;
  set: (v: boolean) => void;
}

// Значение читаем при старте, чтобы режим не слетал при перезагрузке страницы.
function initial(): boolean {
  return localStorage.getItem(KEY) === "1";
}

export const useAdminEdit = create<AdminEditState>((set) => ({
  enabled: initial(),
  toggle: () =>
    set((s) => {
      const next = !s.enabled;
      localStorage.setItem(KEY, next ? "1" : "0");
      return { enabled: next };
    }),
  set: (v: boolean) => {
    localStorage.setItem(KEY, v ? "1" : "0");
    set({ enabled: v });
  },
}));

// Читается из axios-перехватчика (вне React-компонента).
export function adminEditEnabled(): boolean {
  return localStorage.getItem(KEY) === "1";
}
