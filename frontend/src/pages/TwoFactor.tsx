import { useEffect, useState } from "react";
import { ShieldCheck, ShieldAlert, Copy, Check, AlertTriangle, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";

interface EnrollResponse {
  secret: string;
  otpauth_uri: string;
  qr_svg: string;
}

export default function TwoFactorPage() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [enrolling, setEnrolling] = useState<EnrollResponse | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // Backup codes are returned exactly once after successful verify.
  const [justEnabled, setJustEnabled] = useState<string[] | null>(null);
  const [copied, setCopied] = useState(false);

  async function refresh() {
    const r = await api.get<{ enabled: boolean }>("/2fa/status");
    setEnabled(r.data.enabled);
  }

  useEffect(() => { refresh(); }, []);

  async function startEnroll() {
    setErr(null);
    setBusy(true);
    try {
      const r = await api.post<EnrollResponse>("/2fa/enroll");
      setEnrolling(r.data);
    } catch (e: any) {
      setErr(e.response?.data?.detail ?? "Enrollment failed");
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const r = await api.post<{ enabled: boolean; backup_codes: string[] }>("/2fa/verify", { code });
      setJustEnabled(r.data.backup_codes);
      setEnrolling(null);
      setCode("");
      setEnabled(true);
    } catch (e: any) {
      setErr(e.response?.data?.detail ?? "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  async function disable(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await api.post("/2fa/disable", { code });
      setEnabled(false);
      setCode("");
    } catch (e: any) {
      setErr(e.response?.data?.detail ?? "Failed to disable");
    } finally {
      setBusy(false);
    }
  }

  function copyBackup() {
    if (!justEnabled) return;
    navigator.clipboard.writeText(justEnabled.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-2xl mx-auto space-y-4">
      <header>
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
          {enabled ? <ShieldCheck className="size-6 text-emerald-500" /> : <ShieldAlert className="size-6 text-amber-500" />}
          Two-factor authentication
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Add a second step at sign-in using an authenticator app (Google Authenticator, 1Password, Authy, etc.).
        </p>
      </header>

      {/* Status banner */}
      <Card className="p-4 flex items-center gap-3">
        <Badge variant={enabled ? "success" : "warning"}>
          {enabled === null ? "Loading…" : enabled ? "Enabled" : "Disabled"}
        </Badge>
        {!enabled && enabled !== null && !enrolling && (
          <Button onClick={startEnroll} disabled={busy} size="sm">
            {busy ? <><Loader2 className="size-4 animate-spin" /> …</> : "Enable 2FA"}
          </Button>
        )}
      </Card>

      {/* One-time backup-code reveal */}
      {justEnabled && (
        <Card className="p-4 border-2 border-amber-500 bg-amber-500/5">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-semibold">
            <AlertTriangle className="size-4" /> Save your backup codes
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Each code works once. If you lose your authenticator app, you'll need these to get back in.
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm bg-zinc-950 text-emerald-300 p-3 rounded">
            {justEnabled.map((c) => <code key={c}>{c}</code>)}
          </div>
          <div className="mt-3 flex gap-2">
            <Button size="sm" onClick={copyBackup}>
              {copied ? <><Check className="size-3.5" /> Copied</> : <><Copy className="size-3.5" /> Copy all</>}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setJustEnabled(null)}>I've saved them</Button>
          </div>
        </Card>
      )}

      {/* Step 2 of enroll: scan + verify */}
      {enrolling && (
        <Card className="p-5 space-y-4">
          <h2 className="font-semibold">Scan with your authenticator app</h2>
          <div className="mx-auto w-fit bg-white p-3 rounded" dangerouslySetInnerHTML={{ __html: enrolling.qr_svg }} />
          <details className="text-xs text-zinc-500">
            <summary className="cursor-pointer">Can't scan? Enter the secret manually</summary>
            <code className="block mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded font-mono select-all">{enrolling.secret}</code>
          </details>

          <form onSubmit={verifyCode} className="space-y-2">
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Enter the 6-digit code from your app</span>
              <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="000000" maxLength={6} required pattern="[0-9]{6}" />
            </label>
            {err && <p className="text-sm text-rose-600">{err}</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={busy}>
                {busy ? <><Loader2 className="size-4 animate-spin" /> Verifying…</> : "Verify & enable"}
              </Button>
              <Button type="button" variant="outline" onClick={() => { setEnrolling(null); setErr(null); }}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Disable form (only when enabled) */}
      {enabled && !enrolling && (
        <Card className="p-5 space-y-3">
          <h2 className="font-semibold text-rose-600">Disable 2FA</h2>
          <p className="text-xs text-zinc-500">Enter a current code from your authenticator to disable. (Backup codes don't work here for security.)</p>
          <form onSubmit={disable} className="flex items-end gap-2">
            <label className="block flex-1">
              <span className="text-xs text-zinc-500 block mb-1">Current code</span>
              <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="000000" maxLength={6} required />
            </label>
            <Button type="submit" variant="danger" disabled={busy}>Disable</Button>
          </form>
          {err && <p className="text-sm text-rose-600">{err}</p>}
        </Card>
      )}
    </div>
  );
}
