import { useEffect, useState } from "react";
import { Users as UsersIcon, Search, Plus, Download, Loader2, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import type { User, UserRole } from "@/types";

const ROLES: UserRole[] = ["admin", "manager", "employee", "developer"];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: "", full_name: "", password: "", role: "employee" as UserRole,
    is_active: true, is_verified: true,
  });
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState<string | null>(null);

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

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true); setCreateErr(null);
    try {
      await api.post("/users", createForm);
      setCreateForm({ email: "", full_name: "", password: "", role: "employee", is_active: true, is_verified: true });
      setShowCreate(false);
      load();
    } catch (err: any) {
      setCreateErr(err.response?.data?.detail ?? "Create failed");
    } finally {
      setCreating(false);
    }
  }

  // Export downloads the file directly. We use axios responseType:'blob' so we
  // can read the body bytes and trigger a download with the right filename.
  async function exportUsers(format: "csv" | "json") {
    const r = await api.get(`/users/export?format=${format}`, { responseType: "blob" });
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `users.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-4">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><UsersIcon className="size-6" /> Users</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => exportUsers("csv")}><Download className="size-4" /> CSV</Button>
          <Button variant="outline" size="sm" onClick={() => exportUsers("json")}><Download className="size-4" /> JSON</Button>
          <Button size="sm" onClick={() => setShowCreate((s) => !s)}>
            {showCreate ? <><X className="size-4" /> Close</> : <><Plus className="size-4" /> Create user</>}
          </Button>
        </div>
      </header>

      {showCreate && (
        <Card className="p-4">
          <form onSubmit={createUser} className="grid sm:grid-cols-2 gap-3">
            <Field label="Email">
              <Input type="email" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} required />
            </Field>
            <Field label="Full name">
              <Input value={createForm.full_name} onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })} required />
            </Field>
            <Field label="Password (min 8 chars)">
              <Input type="password" value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} required minLength={8} />
            </Field>
            <Field label="Role">
              <Select value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as UserRole })}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </Select>
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={createForm.is_active} onChange={(e) => setCreateForm({ ...createForm, is_active: e.target.checked })} />
              Active immediately
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={createForm.is_verified} onChange={(e) => setCreateForm({ ...createForm, is_verified: e.target.checked })} />
              Pre-verified email
            </label>
            {createErr && <p className="sm:col-span-2 text-sm text-rose-600">{createErr}</p>}
            <div className="sm:col-span-2">
              <Button type="submit" disabled={creating}>
                {creating ? <><Loader2 className="size-4 animate-spin" /> Creating…</> : "Create user"}
              </Button>
            </div>
          </form>
        </Card>
      )}

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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-xs text-zinc-500 block mb-1">{label}</span>
      {children}
    </label>
  );
}
