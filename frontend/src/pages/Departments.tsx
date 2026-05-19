import { useEffect, useState } from "react";
import { Building2, Plus, Trash } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { Department } from "@/types";

export default function DepartmentsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canEdit = role === "admin";
  const [items, setItems] = useState<Department[]>([]);
  const [form, setForm] = useState({ name: "", description: "" });

  async function load() {
    const r = await api.get<Department[]>("/departments");
    setItems(r.data);
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    await api.post("/departments", form);
    setForm({ name: "", description: "" });
    load();
  }
  async function remove(id: number) {
    if (!confirm("Delete department?")) return;
    await api.delete(`/departments/${id}`);
    load();
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

      <Card className="p-0">
        <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {items.map((d) => (
            <li key={d.id} className="p-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="font-medium">{d.name}</div>
                <div className="text-xs text-zinc-500 truncate">{d.description}</div>
              </div>
              {canEdit && (
                <button onClick={() => remove(d.id)} className="p-2 hover:bg-rose-500/10 rounded text-rose-500"><Trash className="size-4" /></button>
              )}
            </li>
          ))}
          {items.length === 0 && <li className="p-6 text-center text-sm text-zinc-500">No departments.</li>}
        </ul>
      </Card>
    </div>
  );
}
