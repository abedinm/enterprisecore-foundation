import { describe, expect, it, beforeEach } from "vitest";
import { useThemeStore } from "@/store/theme";

describe("theme store", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("defaults to 'system'", () => {
    expect(useThemeStore.getState().theme).toBe("system");
  });

  it("setTheme('dark') adds the dark class on <html>", () => {
    useThemeStore.getState().setTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(useThemeStore.getState().theme).toBe("dark");
  });

  it("setTheme('light') removes the dark class", () => {
    useThemeStore.getState().setTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    useThemeStore.getState().setTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
