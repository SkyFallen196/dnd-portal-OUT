// Axios-клиент: сам подставляет токен и адрес API.
import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
export const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://127.0.0.1:8000";

const TOKEN_KEY = "dnd_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({ baseURL: API_URL });

// Перед каждым запросом добавляем заголовок Authorization, если есть токен,
// и флаг «Режима редактирования» админа (сервер по нему решает, давать ли права мастера).
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (localStorage.getItem("dnd_admin_edit") === "1") {
    config.headers["X-Admin-Edit"] = "1";
  }
  return config;
});

// Если сервер ответил 401 — токен протух, разлогиниваем.
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      if (!location.pathname.startsWith("/login")) {
        location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Разовое разрешение админу тронуть ЧУЖУЮ комнату.
//
// Обычно права мастера админ включает тумблером в шапке комнаты. Но удалить чужую комнату
// можно и снаружи — из списка комнат и из админ-панели, где тумблера нет. Для таких точечных
// действий заголовок отправляется только на один конкретный запрос, причём после явного
// подтверждения: смысл режима — защита от случайного изменения, и подтверждение его выполняет.
export const adminEditOnce = { headers: { "X-Admin-Edit": "1" } };

// Удобно достать текст ошибки из ответа FastAPI.
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
    return err.message;
  }
  return "Неизвестная ошибка";
}
