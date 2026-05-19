import { useEffect, useState } from "react";
import { Building2, Plus, Trash, ChevronDown, ChevronRight, UserPlus, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { Department, User } from "@/types";

interface UserListItem {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  department_id: number | null;
}

export default function DepartmentsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canEdit = role === "admin";
  const [items, setItems] = useState<Department[]>([]);
  const [form, setForm] = useState({ name: "", description: "" });

  // members[deptId] = list of users
  const [members, setMembers] = useState<Record<number, UserListItem[]>>({});
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  // For admin: full user list, used in the "Add member" select
  const [allUsers, setAllUsers] = useState<UserListItem[]>([]);
  const [picker, setPicker] = useState<Record<number, number>>({}); // deptId → selected userId

  async function load() {
    const r = await api.get<Department[]>("/departments");
    setItems(r.data);
    if (canEdit) {
      const u = await api.get<UserListItem[]>("/users");
      setAllUsers(u.data);
    }
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    await api.post("/departments", form);
    setForm({ name: "", description: "" });
    load();
  }

  async function removeDept(id: number) {
    if (!confirm("Delete department? Members will be detached.")) return;
    await api.delete(`/departments/${id}`);
    load();
  }

  async function toggle(deptId: number) {
    const next = new Set(expanded);
    if (next.has(deptId)) { next.delete(deptId); }
    else {
      next.add(deptId);
      if (!members[deptId]) {
        const r = await api.get<UserListItem[]>(`/departments/${deptId}/members`);
        setMembers((m) => ({ ...m, [deptId]: r.data }));
      }
    }
    setExpanded(next);
  }

  async function addMember(deptId: number) {
    const uid = picker[deptId];
    if (!uid) return;
    await api.post(`/departments/${deptId}/members/${uid}`);
    const r = await api.get<UserListItem[]>(`/departments/${deptId}/members`);
    setMembers((m) => ({ ...m, [deptId]: r.data }));
    setPicker((p) => ({ ...p, [deptId]: 0 }));
  }

  async function removeMember(deptId: number, userId: number) {
    await api.delete(`/departments/${deptId}/members/${userId}`);
    const r = await api.get<UserListItem[]>(`/departments/${deptId}/members`);
    setMembers((m) => ({ ...m, [deptId]: r.data }));
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><Building2 className="size-6" /> Departments</h1>

      {canEdit && (
        <Card className="p-3">
          <form onSubmit={create} className="grid sm:grid-cols-[1fr_2fr_auto] gap-2 items-end">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <Button type="submit"><Plus className="size-4" /> Add</Button>
          </form>
        </Card>
      )}

      <div className="space-y-2">
        {items.map((d) => {
          const isOpen = expanded.has(d.id);
          const deptMembers = members[d.id] ?? [];
          const available = allUsers.filter((u) => u.department_id !== d.id);
          return (
            <Card key={d.id} className="overflow-hidden">
              <button
                onClick={() => toggle(d.id)}
                className="w-full p-3 flex items-center gap-3 text-left hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
              >
                {isOpen ? <ChevronDown className="size-4 text-zinc-400" /> : <ChevronRight className="size-4 text-zinc-400" />}
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{d.name}</div>
                  <div className="text-xs text-zinc-500 truncate">{d.description}</div>
                </div>
                {canEdit && (
                  <button onClick={(e) => { e.stopPropagation(); removeDept(d.id); }} className="p-2 hover:bg-rose-500/10 rounded text-rose-500">
                    <Trash className="size-4" />
                  </button>
                )}
              </button>

              {isOpen && (
                <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
                  {deptMembers.length === 0 ? (
                    <p className="text-xs text-zinc-500">No members yet.</p>
                  ) : (
                    <ul className="space-y-1">
                      {deptMembers.map((m) => (
                        <li key={m.id} className="flex items-center gap-2 py-1">
                          <span className="size-6 rounded-full bg-brand-500/20 text-brand-700 dark:text-brand-300 text-xs grid place-items-center font-semibold">
                            {m.full_name.slice(0, 1).toUpperCase()}
                          </span>
                          <span className="text-sm flex-1 truncate">{m.full_name}</span>
                          <span className="text-xs text-zinc-500 truncate">{m.email}</span>
                          {canEdit && (
                            <button onClick={() => removeMember(d.id, m.id)} className="p-1 hover:bg-rose-500/10 rounded text-rose-500" title="Remove from department">
                              <X className="size-3.5" />
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}

                  {canEdit && available.length > 0 && (
                    <div className="flex items-center gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                      <Select
                        value={picker[d.id] ?? 0}
                        onChange={(e) => setPicker((p) => ({ ...p, [d.id]: Number(e.target.value) }))}
                        className="flex-1"
                      >
                        <option value={0}>Pick a user to add…</option>
                        {available.map((u) => (
                          <option key={u.id} value={u.id}>{u.full_name} — {u.email}</option>
                        ))}
                      </Select>
                      <Button size="sm" onClick={() => addMember(d.id)} disabled={!picker[d.id]}>
                        <UserPlus className="size-3.5" /> Add
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
        {items.length === 0 && <Card className="p-6 text-center text-sm text-zinc-500">No departments.</Card>}
      </div>
    </div>
  );
}
