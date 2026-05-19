import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { TokenPair, User } from "@/types";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setUser, setTokens } = useAuthStore();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/register", form);
      const tokens = await api.post<TokenPair>("/auth/login", { email: form.email, password: form.password });
      setTokens(tokens.data.access_token, tokens.data.refresh_token, tokens.data.expires_in);
      const me = await api.get<User>("/auth/me");
      setUser(me.data);
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Registration failed");
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
          <h1 className="text-2xl font-bold mt-3">Create account</h1>
          <p className="text-sm text-zinc-500 mt-1">Self-signup starts you as an Employee.</p>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Full name</span>
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </label>
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Email</span>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label className="block">
            <span className="text-xs text-zinc-500 block mb-1">Password (min 8 chars)</span>
            <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </label>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? <><Loader2 className="size-4 animate-spin" /> Creating…</> : "Create account"}
          </Button>
          <p className="text-xs text-center text-zinc-500">
            Already have one? <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link>
          </p>
        </form>
      </Card>
    </div>
  );
}
