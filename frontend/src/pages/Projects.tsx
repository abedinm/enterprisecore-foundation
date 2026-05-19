import { useEffect, useState } from "react";
import { FolderKanban, Plus } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { Project, ProjectStatus } from "@/types";

const STATUS_COLOR: Record<ProjectStatus, "info" | "success" | "warning" | "default" | "danger"> = {
  planning: "info", active: "success", on_hold: "warning", completed: "default", archived: "danger"
};

export default function ProjectsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canCreate = role === "admin" || role === "manager";
  const [projects, setProjects] = useState<Project[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", status: "planning" as ProjectStatus });

  async function load() {
    const r = await api.get<Project[]>("/projects");
    setProjects(r.data);
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    await api.post<Project>("/projects", form);
    setForm({ name: "", description: "", status: "planning" });
    setShowForm(false);
    load();
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-4">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><FolderKanban className="size-6" /> Projects</h1>
        {canCreate && (
          <Button onClick={() => setShowForm((s) => !s)}><Plus className="size-4" /> {showForm ? "Close" : "New project"}</Button>
        )}
      </header>

      {showForm && canCreate && (
        <Card className="p-4">
          <form onSubmit={create} className="grid sm:grid-cols-[1fr_140px_auto] gap-2 items-end">
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Name</span>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </label>
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Status</span>
              <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ProjectStatus })}>
                <option value="planning">Planning</option><option value="active">Active</option><option value="on_hold">On hold</option><option value="completed">Completed</option><option value="archived">Archived</option>
              </Select>
            </label>
            <Button type="submit">Create</Button>
            <label className="sm:col-span-3 block">
              <span className="text-xs text-zinc-500 block mb-1">Description</span>
              <Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
          </form>
        </Card>
      )}

      {projects.length === 0 ? (
        <Card className="p-8 text-center text-sm text-zinc-500">No projects yet.</Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {projects.map((p) => (
            <Card key={p.id} className="p-4">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold">{p.name}</h3>
                <Badge variant={STATUS_COLOR[p.status]} className="capitalize">{p.status.replace("_", " ")}</Badge>
              </div>
              <p className="text-sm text-zinc-500 line-clamp-3">{p.description || "No description"}</p>
              <p className="text-[10px] text-zinc-400 mt-3">Created {new Date(p.created_at).toLocaleDateString()}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
