import { create } from "zustand";

export interface AuthUser {
  user_id: string;
  email: string;
  display_name: string;
  created_at: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  setAuth: (user: AuthUser, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  setAccessToken: (token: string) => void;
  loadFromStorage: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,

  setAuth: (user, accessToken, refreshToken) => {
    localStorage.setItem("rz_access", accessToken);
    localStorage.setItem("rz_refresh", refreshToken);
    localStorage.setItem("rz_user", JSON.stringify(user));
    set({ user, accessToken, refreshToken, isAuthenticated: true });
  },

  clearAuth: () => {
    localStorage.removeItem("rz_access");
    localStorage.removeItem("rz_refresh");
    localStorage.removeItem("rz_user");
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },

  setAccessToken: (token) => {
    localStorage.setItem("rz_access", token);
    set({ accessToken: token });
  },

  loadFromStorage: () => {
    const accessToken = localStorage.getItem("rz_access");
    const refreshToken = localStorage.getItem("rz_refresh");
    const raw = localStorage.getItem("rz_user");
    if (accessToken && refreshToken && raw) {
      try {
        const user = JSON.parse(raw) as AuthUser;
        set({ user, accessToken, refreshToken, isAuthenticated: true });
      } catch {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      }
    }
  },
}));