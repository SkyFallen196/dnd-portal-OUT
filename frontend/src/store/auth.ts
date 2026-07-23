// Глобальное состояние авторизации (zustand).
import { create } from "zustand";
import { api, clearToken, setToken } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  // Загружает текущего пользователя по сохранённому токену.
  fetchMe: () => Promise<void>;
  login: (token: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  fetchMe: async () => {
    try {
      const { data } = await api.get<User>("/auth/me");
      set({ user: data, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
  login: async (token: string) => {
    setToken(token);
    const { data } = await api.get<User>("/auth/me");
    set({ user: data, loading: false });
  },
  logout: () => {
    clearToken();
    set({ user: null });
  },
  setUser: (user: User) => set({ user }),
}));

// Активна ли подписка (или пользователь — админ).
export function hasActiveSubscription(user: User | null): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  if (!user.subscription_expires_at) return false;
  return new Date(user.subscription_expires_at) > new Date();
}
