// Theme store. The actual `dark` class on <html> is set in index.html before
// React mounts (to avoid a flash) and is kept in sync by `applyTheme`.

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
}

function applyTheme(t: Theme) {
  const isDark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "system",
      setTheme: (t) => {
        applyTheme(t);
        set({ theme: t });
      }
    }),
    {
      name: "ec-theme-store",
      onRehydrateStorage: () => (state) => { if (state) applyTheme(state.theme); }
    }
  )
);
