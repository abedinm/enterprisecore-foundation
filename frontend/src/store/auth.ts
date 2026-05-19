// Auth state — persisted to localStorage so the user stays logged in across reloads.

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null; // ms epoch
  setUser: (u: User | null) => void;
  setTokens: (access: string, refresh: string, expiresIn: number) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      setUser: (u) => set({ user: u }),
      setTokens: (access, refresh, expiresIn) =>
        set({ accessToken: access, refreshToken: refresh, expiresAt: Date.now() + expiresIn * 1000 }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null, expiresAt: null })
    }),
    { name: "ec-auth" }
  )
);
