import { useEffect, useState } from "react";
import { Users, FolderKanban, ListChecks, Bell, TrendingUp, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { DashboardStats } from "@/types";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<DashboardStats>("/system/dashboard").then((r) => setStats(r.data)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <header>
        <p className="text-sm text-zinc-500">
          Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"},
        </p>
        <h1 className="text-2xl md:text-3xl font-bold">{user?.full_name}</h1>
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="brand" className="capitalize">{user?.role}</Badge>
          {user?.is_verified && <Badge variant="success">Verified</Badge>}
        </div>
      </header>

      {loading ? (
        <div className="text-sm text-zinc-500">Loading…</div>
      ) : stats ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard icon={<Users className="size-5" />}         label="Total Users"   value={stats.users.total}            sub={`+${stats.users.new_last_7d} last 7d`} />
            <StatCard icon={<FolderKanban className="size-5" />} label="Projects"     value={stats.projects.total} />
            <StatCard icon={<ListChecks className="size-5" />}   label="Tasks"        value={stats.tasks.total}            sub={`${stats.tasks.completion_rate}% done`} />
            <StatCard icon={<Bell className="size-5" />}         label="Unread Notif" value={stats.my_unread_notifications} />
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-5">
              <h2 className="font-semibold mb-3 flex items-center gap-2"><TrendingUp className="size-4" /> Users by role</h2>
              <ul className="space-y-2">
                {Object.entries(stats.users.by_role).map(([role, n]) => (
                  <li key={role} className="flex items-center justify-between">
                    <span className="capitalize text-sm">{role}</span>
                    <div className="flex-1 mx-4 h-2 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                      <div className="h-full bg-brand-500" style={{ width: `${(n / Math.max(1, stats.users.total)) * 100}%` }} />
                    </div>
                    <span className="text-sm font-mono">{n}</span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-5">
              <h2 className="font-semibold mb-3 flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-500" /> Task progress</h2>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Done</span>
                  <span className="font-mono">{stats.tasks.done} / {stats.tasks.total}</span>
                </div>
                <div className="h-3 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600" style={{ width: `${stats.tasks.completion_rate}%` }} />
                </div>
                <p className="text-xs text-zinc-500 mt-2">Active users: <strong>{stats.users.active}</strong> of {stats.users.total}</p>
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: number | string; sub?: string }) {
  return (
    <Card className="p-4">
      <div className="text-brand-600">{icon}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
      {sub && <div className="text-[10px] text-zinc-400 mt-1">{sub}</div>}
    </Card>
  );
}
