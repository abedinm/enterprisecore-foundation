import { useEffect, useState } from "react";
import { Users as UsersIcon, Search } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import type { User, UserRole } from "@/types";

const ROLES: UserRole[] = ["admin", "manager", "employee", "developer"];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState("");

  async function load() {
    const r = await api.get<User[]>("/users", { params: q ? { q } : undefined });
    setUsers(r.data);
  }

  useEffect(() => { load(); }, [q]);

  async function changeRole(id: number, role: UserRole) {
    await api.patch(`/users/${id}`, { role });
    load();
  }
  async function toggleActive(u: User) {
    await api.patch(`/users/${u.id}`, { is_active: !u.is_active });
    load();
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-4">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><UsersIcon className="size-6" /> Users</h1>
      </header>

      <Card className="p-3 flex items-center gap-2">
        <Search className="size-4 text-zinc-500" />
        <Input placeholder="Search by name or email…" value={q} onChange={(e) => setQ(e.target.value)} />
      </Card>

      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 dark:bg-zinc-800/40 text-left text-xs text-zinc-500">
            <tr>
              <th className="p-3">User</th><th>Role</th><th>Active</th><th>Last login</th><th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-zinc-100 dark:border-zinc-800">
                <td className="p-3">
                  <div className="font-medium">{u.full_name}</div>
                  <div className="text-xs text-zinc-500">{u.email}</div>
                </td>
                <td className="p-3">
                  <Select value={u.role} onChange={(e) => changeRole(u.id, e.target.value as UserRole)} className="h-8 capitalize">
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </Select>
                </td>
                <td className="p-3">
                  <button onClick={() => toggleActive(u)}>
                    <Badge variant={u.is_active ? "success" : "danger"}>{u.is_active ? "Active" : "Disabled"}</Badge>
                  </button>
                </td>
                <td className="p-3 text-xs text-zinc-500">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "—"}</td>
                <td className="p-3 text-xs text-zinc-500">{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="p-6 text-center text-sm text-zinc-500">No users match.</p>}
      </Card>
    </div>
  );
}
