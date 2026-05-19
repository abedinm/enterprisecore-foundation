import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Sparkles, Loader2, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { TokenPair, User } from "@/types";

/**
 * Two-stage sign-in:
 *   Stage A: email + password. If the account has 2FA, the API returns 403
 *            with detail "Two-factor code required" — we move to stage B.
 *   Stage B: prompt for the 6-digit TOTP code (or 8-char backup), resubmit.
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser, setTokens } = useAuthStore();
  const [email, setEmail] = useState("admin@enterprisecore.io");
  const [password, setPassword] = useState("Admin123!");
  const [code, setCode] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const body: Record<string, string> = { email, password };
      if (needs2fa && code) body.code = code;
      const tokens = await api.post<TokenPair>("/auth/login", body);
      setTokens(tokens.data.access_token, tokens.data.refresh_token, tokens.data.expires_in);
      const me = await api.get<User>("/auth/me");
      setUser(me.data);
      const from = (location.state as any)?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail ?? "Login failed";
      if (status === 403 && typeof detail === "string" && detail.toLowerCase().includes("two-factor")) {
        // Switch to 2FA stage instead of showing the error.
        setNeeds2fa(true);
        setError(null);
      } else {
        setError(detail);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-brand-50 to-zinc-50 dark:from-zinc-950 dark:to-zinc-900">
      <Card className="w-full max-w-md">
        <div className="p-6 text-center border-b border-zinc-200 dark:border-zinc-800">
          <div className="size-12 mx-auto rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white">
            {needs2fa ? <ShieldCheck className="size-6" /> : <Sparkles className="size-6" />}
          </div>
          <h1 className="text-2xl font-bold mt-3">{needs2fa ? "Two-factor required" : "Sign in"}</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {needs2fa ? "Enter the 6-digit code from your authenticator app." : "Welcome back to EnterpriseCore"}
          </p>
        </div>

        <form onSubmit={submit} className="p-6 space-y-4">
          {!needs2fa ? (
            <>
              <label className="block">
                <span className="text-xs text-zinc-500 block mb-1">Email</span>
                <Input type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} required />
              </label>
              <label className="block">
                <span className="text-xs text-zinc-500 block mb-1">Password</span>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </label>
            </>
          ) : (
            <label className="block">
              <span className="text-xs text-zinc-500 block mb-1">Authenticator code (or backup code)</span>
              <Input
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="000000"
                maxLength={8}
                required
              />
            </label>
          )}
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? <><Loader2 className="size-4 animate-spin" /> Signing in…</> : (needs2fa ? "Verify & sign in" : "Sign in")}
          </Button>
          {needs2fa ? (
            <button type="button" onClick={() => { setNeeds2fa(false); setCode(""); }} className="text-xs text-zinc-500 hover:underline w-full text-center">
              ← Back
            </button>
          ) : (
            <div className="text-xs text-center text-zinc-500 space-y-1">
              <p>No account? <Link to="/register" className="text-brand-600 hover:underline">Create one</Link></p>
              <p><Link to="/forgot-password" className="text-brand-600 hover:underline">Forgot password?</Link></p>
            </div>
          )}
          {!needs2fa && (
            <p className="text-[10px] text-center text-zinc-400">
              Default admin: admin@enterprisecore.io / Admin123!
            </p>
          )}
        </form>
      </Card>
    </div>
  );
}
