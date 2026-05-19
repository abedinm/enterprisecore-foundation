import { useEffect, useState } from "react";
import { KeyRound, Plus, Trash, AlertTriangle, Copy, Check, Ban } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";

interface APIKey {
  id: number;
  user_id: number;
  name: string;
  prefix: string;
  last_used_at?: string | null;
  revoked: boolean;
  created_at: string;
}

interface APIKeyCreateResponse extends APIKey {
  raw_key: string;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  // The raw key is shown exactly once after creation.
  const [justCreated, setJustCreated] = useState<APIKeyCreateResponse | null>(null);
  const [copied, setCopied] = useState(false);

  async function load() {
    const r = await api.get<APIKey[]>("/api-keys");
    setKeys(r.data);
  }
  useEffect(() => { load(); }, []);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const r = await api.post<APIKeyCreateResponse>("/api-keys", { name });
      setJustCreated(r.data);
      setName("");
      load();
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: number) {
    await api.post(`/api-keys/${id}/revoke`);
    load();
  }

  async function remove(id: number) {
    if (!confirm("Permanently delete this API key?")) return;
    await api.delete(`/api-keys/${id}`);
    load();
  }

  function copyRaw() {
    if (!justCreated) return;
    navigator.clipboard.writeText(justCreated.raw_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><KeyRound className="size-6" /> API keys</h1>
      <p className="text-sm text-zinc-500">
        Use these to call the API as your account from CI, scripts, or external services.
        The raw key is shown only once at creation — store it in a secret manager.
      </p>

      {/* One-time raw key reveal */}
      {justCreated && (
        <Card className="p-4 border-2 border-amber-500 bg-amber-500/5">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold">
            <AlertTriangle className="size-4" /> Save this key now — you won't see it again
          </div>
          <p className="text-xs text-zinc-500 mt-1">Name: <strong>{justCreated.name}</strong>  ·  Prefix: <code>{justCreated.prefix}</code></p>
          <div className="mt-3 flex gap-2">
            <code className="flex-1 p-2 rounded bg-zinc-950 text-emerald-300 font-mono text-xs overflow-x-auto whitespace-nowrap">
              {justCreated.raw_key}
            </code>
            <Button size="sm" onClick={copyRaw}>
              {copied ? <><Check className="size-3.5" /> Copied</> : <><Copy className="size-3.5" /> Copy</>}
            </Button>
          </div>
          <button onClick={() => setJustCreated(null)} className="mt-3 text-xs text-zinc-500 hover:underline">
            I've saved it — dismiss
          </button>
        </Card>
      )}

      {/* Create form */}
      <Card className="p-3">
        <form
          onSubmit={(e) => { e.preventDefault(); create(); }}
          className="grid sm:grid-cols-[1fr_auto] gap-2 items-end"
        >
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Name (what is this key for?)</span>
            <Input
              placeholder="e.g. GitHub Actions CI"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <Button type="submit" disabled={busy}><Plus className="size-4" /> Create</Button>
        </form>
      </Card>

      {/* Existing keys */}
      {keys.length === 0 ? (
        <Card className="p-8 text-center text-sm text-zinc-500">No API keys yet.</Card>
      ) : (
        <Card className="p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 dark:bg-zinc-800/40 text-xs text-zinc-500 text-left">
              <tr>
                <th className="p-3">Name</th>
                <th>Prefix</th>
                <th>Created</th>
                <th>Last used</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="p-3 font-medium">{k.name}</td>
                  <td className="p-3 font-mono text-xs">{k.prefix}…</td>
                  <td className="p-3 text-xs text-zinc-500">{new Date(k.created_at).toLocaleDateString()}</td>
                  <td className="p-3 text-xs text-zinc-500">{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "—"}</td>
                  <td className="p-3">
                    {k.revoked
                      ? <Badge variant="danger">Revoked</Badge>
                      : <Badge variant="success">Active</Badge>}
                  </td>
                  <td className="p-3 text-right">
                    {!k.revoked && (
                      <button onClick={() => revoke(k.id)} title="Revoke" className="p-1 hover:bg-amber-500/10 rounded text-amber-600">
                        <Ban className="size-4" />
                      </button>
                    )}
                    <button onClick={() => remove(k.id)} title="Delete" className="p-1 hover:bg-rose-500/10 rounded text-rose-500 ml-1">
                      <Trash className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
