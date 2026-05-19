import { useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, Loader2, Mail } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import axios from "axios";

/**
 * Token-based password reset, two steps:
 *   1. Enter email → get a token (in dev, returned in JSON; in prod, emailed).
 *   2. Paste token + new password → reset.
 *
 * We use plain axios (not the auth-aware client) because no auth is needed
 * and we want raw 200 responses without the refresh-retry interceptor.
 */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  async function requestToken(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setMsg(null);
    try {
      const r = await axios.post("/api/v1/auth/password-reset/request", { email });
      if (r.data?.dev_token) {
        setToken(r.data.dev_token);
        setMsg({ type: "ok", text: "Dev mode: token shown below. In production this would be emailed." });
      } else {
        setMsg({ type: "ok", text: r.data?.message ?? "If the email is registered, a reset link has been sent." });
      }
      setStep(2);
    } catch (err: any) {
      setMsg({ type: "err", text: err.response?.data?.detail ?? "Request failed" });
    } finally {
      setBusy(false);
    }
  }

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) {
      setMsg({ type: "err", text: "Password must be at least 8 characters." });
      return;
    }
    setBusy(true); setMsg(null);
    try {
      await axios.post("/api/v1/auth/password-reset/confirm", { token, new_password: newPassword });
      setMsg({ type: "ok", text: "Password updated! You can now sign in with your new password." });
    } catch (err: any) {
      setMsg({ type: "err", text: err.response?.data?.detail ?? "Reset failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-brand-50 to-zinc-50 dark:from-zinc-950 dark:to-zinc-900">
      <Card className="w-full max-w-md">
        <div className="p-6 text-center border-b border-zinc-200 dark:border-zinc-800">
          <div className="size-12 mx-auto rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white">
            <KeyRound className="size-6" />
          </div>
          <h1 className="text-2xl font-bold mt-3">Reset password</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {step === 1 ? "Enter the email associated with your account." : "Paste the token you received and set a new password."}
          </p>
        </div>

        {step === 1 ? (
          <form onSubmit={requestToken} className="p-6 space-y-4">
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Email</span>
              <Input type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? <><Loader2 className="size-4 animate-spin" /> Sending…</> : <><Mail className="size-4" /> Send reset token</>}
            </Button>
          </form>
        ) : (
          <form onSubmit={confirm} className="p-6 space-y-4">
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Token</span>
              <Input value={token} onChange={(e) => setToken(e.target.value)} required />
            </label>
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">New password (min 8 chars)</span>
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            </label>
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? <><Loader2 className="size-4 animate-spin" /> Resetting…</> : "Reset password"}
            </Button>
            <button type="button" onClick={() => setStep(1)} className="text-xs text-zinc-500 hover:underline">
              ← Back to email entry
            </button>
          </form>
        )}

        {msg && (
          <div className="px-6 pb-4">
            <Badge variant={msg.type === "ok" ? "success" : "danger"} className="block w-full px-3 py-2 text-center">
              {msg.text}
            </Badge>
          </div>
        )}

        <div className="px-6 pb-6 text-center">
          <Link to="/login" className="text-xs text-brand-600 hover:underline">Back to sign in</Link>
        </div>
      </Card>
    </div>
  );
}
