import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { TokenPair, User } from "@/types";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser, setTokens } = useAuthStore();
  const [email, setEmail] = useState("admin@enterprisecore.io");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await api.post<TokenPair>("/auth/login", { email, password });
      setTokens(tokens.data.access_token, tokens.data.refresh_token, tokens.data.expires_in);
      const me = await api.get<User>("/auth/me");
      setUser(me.data);
      const from = (location.state as any)?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-brand-50 to-zinc-50 dark:from-zinc-950 dark:to-zinc-900">
      <Card className="w-full max-w-md">
        <div className="p-6 text-center border-b border-zinc-200 dark:border-zinc-800">
          <div className="size-12 mx-auto rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 grid place-items-center text-white">
            <Sparkles className="size-6" />
          </div>
          <h1 className="text-2xl font-bold mt-3">Sign in</h1>
          <p className="text-sm text-zinc-500 mt-1">Welcome back to EnterpriseCore</p>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Email</span>
            <Input type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Password</span>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? <><Loader2 className="size-4 animate-spin" /> Signing in…</> : "Sign in"}
          </Button>
          <p className="text-xs text-center text-zinc-500">
            No account? <Link to="/register" className="text-brand-600 hover:underline">Create one</Link>
          </p>
          <p className="text-[10px] text-center text-zinc-400">
            Default admin: admin@enterprisecore.io / Admin123!
          </p>
        </form>
      </Card>
    </div>
  );
}
