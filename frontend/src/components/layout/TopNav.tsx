import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, LogOut, Moon, Sun, MonitorSmartphone, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import { useNotificationStore } from "@/store/notifications";
import { api } from "@/api/client";
import { cn } from "@/lib/cn";

export function TopNav() {
  const { user, refreshToken, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const { unread, items, fetch, markRead, markAllRead, connectWS, disconnectWS, wsConnected } = useNotificationStore();
  const navigate = useNavigate();

  const [openBell, setOpenBell] = useState(false);
  const [openProfile, setOpenProfile] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  // Initial fetch + WebSocket connect.
  // The poll-every-60s acts as a redundancy mechanism if the WS drops.
  useEffect(() => {
    fetch();
    connectWS();
    const t = setInterval(fetch, 60_000);
    return () => { clearInterval(t); disconnectWS(); };
  }, [fetch, connectWS, disconnectWS]);

  // Close dropdowns on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setOpenBell(false);
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setOpenProfile(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function doLogout() {
    try {
      if (refreshToken) await api.post("/auth/logout", { refresh_token: refreshToken });
    } catch { /* ignore */ }
    logout();
    navigate("/login");
  }

  const nextTheme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
  const ThemeIcon = theme === "dark" ? Sun : theme === "light" ? Moon : MonitorSmartphone;

  return (
    <header className="h-14 sticky top-0 z-30 border-b border-zinc-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 backdrop-blur flex items-center px-4 gap-3">
      <Link to="/" className="lg:hidden font-semibold flex items-center gap-2">
        <span className="size-6 rounded-md bg-brand-600 text-white text-xs grid place-items-center">EC</span>
        EnterpriseCore
      </Link>

      <div className="flex-1" />

      {/* Theme toggle */}
      <button
        onClick={() => setTheme(nextTheme)}
        className="h-9 w-9 grid place-items-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800"
        title={`Theme: ${theme} (click → ${nextTheme})`}
      >
        <ThemeIcon className="size-4" />
      </button>

      {/* Notifications */}
      <div className="relative" ref={bellRef}>
        <button
          onClick={() => setOpenBell((o) => !o)}
          className="h-9 w-9 grid place-items-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 relative"
          title={wsConnected ? "Notifications (live)" : "Notifications (polling)"}
        >
          <Bell className="size-4" />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-600 text-white text-[10px] font-bold grid place-items-center">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
          {/* Tiny green dot when WebSocket is connected. */}
          {wsConnected && (
            <span className="absolute bottom-0 right-0 size-1.5 rounded-full bg-emerald-500 ring-1 ring-white dark:ring-zinc-900" />
          )}
        </button>
        {openBell && (
          <div className="absolute right-0 top-11 w-80 max-h-[70vh] overflow-y-auto rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-lg scrollbar-thin">
            <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <span className="font-semibold text-sm">Notifications</span>
              <button onClick={markAllRead} className="text-xs text-brand-600 hover:underline">Mark all read</button>
            </div>
            {items.length === 0 ? (
              <p className="p-6 text-center text-sm text-zinc-500">You're all caught up.</p>
            ) : (
              <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {items.map((n) => (
                  <li key={n.id} className={cn("p-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/40", !n.read && "bg-brand-500/5")}>
                    <button onClick={() => markRead(n.id)} className="text-left w-full">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={
                          n.type === "error" ? "danger" :
                          n.type === "warning" ? "warning" :
                          n.type === "success" ? "success" :
                          n.type === "system" ? "info" : "default"
                        }>{n.type}</Badge>
                        {!n.read && <span className="size-1.5 rounded-full bg-brand-500" />}
                      </div>
                      <div className="text-sm font-medium">{n.title}</div>
                      <div className="text-xs text-zinc-500 line-clamp-2">{n.message}</div>
                      <div className="text-[10px] text-zinc-400 mt-1">{new Date(n.created_at).toLocaleString()}</div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="p-2 border-t border-zinc-200 dark:border-zinc-800">
              <Link to="/notifications" onClick={() => setOpenBell(false)} className="block text-center text-xs text-brand-600 hover:underline py-1">View all</Link>
            </div>
          </div>
        )}
      </div>

      {/* Profile */}
      <div className="relative" ref={profileRef}>
        <button
          onClick={() => setOpenProfile((o) => !o)}
          className="h-9 pl-1 pr-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 inline-flex items-center gap-2"
        >
          <span className="size-7 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white text-xs grid place-items-center font-semibold">
            {user?.full_name?.slice(0, 1).toUpperCase() ?? "?"}
          </span>
          <span className="hidden md:block text-sm">{user?.full_name}</span>
          <ChevronDown className="size-3.5" />
        </button>
        {openProfile && (
          <div className="absolute right-0 top-11 w-60 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-lg overflow-hidden">
            <div className="p-3 border-b border-zinc-200 dark:border-zinc-800">
              <div className="font-semibold text-sm">{user?.full_name}</div>
              <div className="text-xs text-zinc-500">{user?.email}</div>
              <Badge variant="brand" className="mt-1 capitalize">{user?.role}</Badge>
            </div>
            <Link to="/settings" onClick={() => setOpenProfile(false)} className="block px-3 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800/60">Account settings</Link>
            <button onClick={doLogout} className="w-full text-left px-3 py-2 text-sm text-rose-600 hover:bg-rose-500/10 inline-flex items-center gap-2">
              <LogOut className="size-4" /> Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
