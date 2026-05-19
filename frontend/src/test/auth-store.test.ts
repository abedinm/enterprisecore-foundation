import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "@/store/auth";

describe("auth store", () => {
  beforeEach(() => {
    // Each test starts from a clean store.
    useAuthStore.getState().logout();
    localStorage.clear();
  });

  it("starts with no user or tokens", () => {
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
    expect(s.refreshToken).toBeNull();
  });

  it("setTokens persists tokens and computes expiry", () => {
    const before = Date.now();
    useAuthStore.getState().setTokens("a", "r", 3600);
    const s = useAuthStore.getState();
    expect(s.accessToken).toBe("a");
    expect(s.refreshToken).toBe("r");
    expect(s.expiresAt).not.toBeNull();
    // Should be roughly 1 hour in the future.
    expect(s.expiresAt! - before).toBeGreaterThan(3_500_000);
    expect(s.expiresAt! - before).toBeLessThan(3_700_000);
  });

  it("setUser stores the user", () => {
    useAuthStore.getState().setUser({
      id: 1, email: "a@b.io", full_name: "A", role: "admin",
      is_active: true, is_verified: true, created_at: new Date().toISOString(),
    });
    expect(useAuthStore.getState().user?.email).toBe("a@b.io");
  });

  it("logout clears everything", () => {
    useAuthStore.getState().setTokens("a", "r", 3600);
    useAuthStore.getState().setUser({
      id: 1, email: "x@y.io", full_name: "X", role: "employee",
      is_active: true, is_verified: false, created_at: new Date().toISOString(),
    });
    useAuthStore.getState().logout();
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
    expect(s.refreshToken).toBeNull();
    expect(s.expiresAt).toBeNull();
  });
});
