import { useEffect, useState } from "react";
import { ListTodo, Plus, Trash } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import type { Task, TaskStatus, TaskPriority, Project } from "@/types";

const STATUSES: TaskStatus[] = ["todo", "in_progress", "review", "done", "cancelled"];
const PRIORITIES: TaskPriority[] = ["low", "medium", "high", "urgent"];

const PRIORITY_VAR: Record<TaskPriority, "default" | "info" | "warning" | "danger"> = {
  low: "default", medium: "info", high: "warning", urgent: "danger"
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({ title: "", project_id: 0, priority: "medium" as TaskPriority });

  async function load() {
    const [t, p] = await Promise.all([api.get<Task[]>("/tasks"), api.get<Project[]>("/projects")]);
    setTasks(t.data);
    setProjects(p.data);
    if (form.project_id === 0 && p.data[0]) setForm((f) => ({ ...f, project_id: p.data[0].id }));
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.project_id) return;
    await api.post<Task>("/tasks", form);
    setForm({ ...form, title: "" });
    load();
  }
  async function setStatus(t: Task, status: TaskStatus) {
    await api.patch(`/tasks/${t.id}`, { status });
    load();
  }
  async function remove(t: Task) {
    if (!confirm(`Delete "${t.title}"?`)) return;
    await api.delete(`/tasks/${t.id}`);
    load();
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-4">
      <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><ListTodo className="size-6" /> Tasks</h1>

      <Card className="p-3">
        <form onSubmit={create} className="grid sm:grid-cols-[1fr_160px_140px_auto] gap-2 items-end">
          <Input placeholder="Task title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          <Select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: Number(e.target.value) })} required>
            <option value={0} disabled>Project…</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as TaskPriority })}>
            {PRIORITIES.map((p) => <option key={p} value={p} className="capitalize">{p}</option>)}
          </Select>
          <Button type="submit"><Plus className="size-4" /> Add</Button>
        </form>
      </Card>

      {tasks.length === 0 ? (
        <Card className="p-8 text-center text-sm text-zinc-500">No tasks. Add your first above.</Card>
      ) : (
        <Card className="p-0">
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {tasks.map((t) => (
              <li key={t.id} className="p-3 flex items-center gap-3">
                <Select value={t.status} onChange={(e) => setStatus(t, e.target.value as TaskStatus)} className="h-8 capitalize w-32">
                  {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                </Select>
                <span className={"flex-1 text-sm truncate " + (t.status === "done" ? "line-through opacity-50" : "")}>{t.title}</span>
                <Badge variant={PRIORITY_VAR[t.priority]} className="capitalize">{t.priority}</Badge>
                <button onClick={() => remove(t)} className="p-2 hover:bg-rose-500/10 rounded text-rose-500"><Trash className="size-4" /></button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
