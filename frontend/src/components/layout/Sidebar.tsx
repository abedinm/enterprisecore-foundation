import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Users, FolderKanban, ListTodo, BellRing,
  ShieldCheck, Building2, Settings, KeyRound, Sparkles
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/cn";

// Each link knows which roles may see it.
const LINKS = [
  { to: "/",                label: "Dashboard",     icon: LayoutDashboard, roles: ["admin","manager","employee","developer"] },
  { to: "/projects",        label: "Projects",      icon: FolderKanban,    roles: ["admin","manager","employee","developer"] },
  { to: "/tasks",           label: "Tasks",         icon: ListTodo,        roles: ["admin","manager","employee","developer"] },
  { to: "/notifications",   label: "Notifications", icon: BellRing,        roles: ["admin","manager","employee","developer"] },
  { to: "/users",           label: "Users",         icon: Users,           roles: ["admin"] },
  { to: "/departments",     label: "Departments",   icon: Building2,       roles: ["admin","manager"] },
  { to: "/audit",           label: "Audit Log",     icon: ShieldCheck,     roles: ["admin"] },
  { to: "/api-keys",        label: "API Keys",      icon: KeyRound,        roles: ["admin","developer"] },
  { to: "/security/2fa",    label: "2FA",           icon: ShieldCheck,     roles: ["admin","manager","employee","developer"] },
];

export function Sidebar() {
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? "employee";

  return (
    <aside className="hidden lg:flex flex-col w-60 shrink-0 h-screen sticky top-0 border-r border-zinc-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 backdrop-blur">
      <div className="px-5 h-14 flex items-center gap-2 font-semibold text-lg border-b border-zinc-200 dark:border-zinc-800">
        <span className="size-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white text-sm">
          <Sparkles className="size-4" />
        </span>
        EnterpriseCore
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto scrollbar-thin">
        {LINKS.filter((l) => l.roles.includes(role)).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition",
                isActive
                  ? "bg-brand-500/10 text-brand-700 dark:text-brand-200 font-medium"
                  : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/60"
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-2 border-t border-zinc-200 dark:border-zinc-800">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm",
              isActive
                ? "bg-brand-500/10 text-brand-700 dark:text-brand-200 font-medium"
                : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800/60"
            )
          }
        >
          <Settings className="size-4" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
