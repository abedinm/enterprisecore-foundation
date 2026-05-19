import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { api } from "@/api/client";

interface AuditRow {
  id: number;
  user_id: number | null;
  action: string;
  target_type: string;
  target_id: string;
  detail: string;
  ip_address: string;
  created_at: string;
}

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.get<AuditRow[]>("/audit", { params: { limit: 200 } }).then((r) => setRows(r.data));
  }, []);

  const filtered = rows.filter((r) =>
    filter === "" ||
    r.action.toLowerCase().includes(filter.toLowerCase()) ||
    r.detail.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto space-y-4">
      <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><ShieldCheck className="size-6" /> Audit log</h1>
      <Card className="p-3">
        <Input placeholder="Filter by action or detail…" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </Card>
      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 dark:bg-zinc-800/40 text-xs text-zinc-500 text-left">
            <tr><th className="p-3">When</th><th>User</th><th>Action</th><th>Target</th><th>Detail</th><th>IP</th></tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id} className="border-t border-zinc-100 dark:border-zinc-800">
                <td className="p-3 text-xs text-zinc-500 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
                <td className="p-3 text-xs">{r.user_id ?? "—"}</td>
                <td className="p-3"><Badge variant="brand">{r.action}</Badge></td>
                <td className="p-3 text-xs">{r.target_type}{r.target_id ? `#${r.target_id}` : ""}</td>
                <td className="p-3 text-xs max-w-xs truncate" title={r.detail}>{r.detail}</td>
                <td className="p-3 text-xs">{r.ip_address || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <p className="p-6 text-center text-sm text-zinc-500">No audit rows.</p>}
      </Card>
    </div>
  );
}
