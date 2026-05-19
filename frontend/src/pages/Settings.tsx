import { useEffect, useState } from "react";
import { Save, Lock, User as UserIcon, Palette, Loader2, Check } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import type { User, SystemSetting } from "@/types";

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const { theme, setTheme } = useThemeStore();

  // Profile state mirrors `user` and is only saved when the user clicks Save.
  const [profile, setProfile] = useState({
    full_name: user?.full_name ?? "",
    bio: user?.bio ?? "",
    phone: user?.phone ?? "",
    avatar_url: user?.avatar_url ?? ""
  });
  const [savedProfile, setSavedProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  // Password state
  const [pwd, setPwd] = useState({ current_password: "", new_password: "" });
  const [pwdMsg, setPwdMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // System settings (admin-only)
  const [sys, setSys] = useState<SystemSetting[] | null>(null);

  useEffect(() => {
    if (user?.role === "admin") {
      api.get<SystemSetting[]>("/settings/system").then((r) => setSys(r.data)).catch(() => setSys([]));
    }
  }, [user?.role]);

  async function saveProfile() {
    setSavingProfile(true);
    try {
      const r = await api.patch<User>("/users/me", profile);
      setUser(r.data);
      setSavedProfile(true);
      setTimeout(() => setSavedProfile(false), 2000);
    } finally {
      setSavingProfile(false);
    }
  }

  async function changePassword() {
    setPwdMsg(null);
    try {
      await api.post("/users/me/password", pwd);
      setPwdMsg({ type: "ok", text: "Password updated. You may need to sign in again on other devices." });
      setPwd({ current_password: "", new_password: "" });
    } catch (err: any) {
      setPwdMsg({ type: "err", text: err.response?.data?.detail ?? "Failed to change password" });
    }
  }

  async function updateSysSetting(key: string, value: string) {
    const r = await api.put<SystemSetting>(`/settings/system/${key}`, { value });
    setSys((prev) => prev?.map((s) => (s.key === key ? r.data : s)) ?? null);
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl md:text-3xl font-bold">Settings</h1>

      {/* ── Profile ───────────────────────────────────────────────────── */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center gap-2 mb-2"><UserIcon className="size-4 text-brand-600" /><h2 className="font-semibold">Profile</h2></div>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Full name">
            <Input value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} />
          </Field>
          <Field label="Phone">
            <Input value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} />
          </Field>
          <Field label="Avatar URL" className="sm:col-span-2">
            <Input value={profile.avatar_url} onChange={(e) => setProfile({ ...profile, avatar_url: e.target.value })} placeholder="https://…" />
          </Field>
          <Field label="Bio" className="sm:col-span-2">
            <Textarea rows={3} value={profile.bio} onChange={(e) => setProfile({ ...profile, bio: e.target.value })} />
          </Field>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={saveProfile} disabled={savingProfile}>
            {savingProfile ? <><Loader2 className="size-4 animate-spin" /> Saving…</> : <><Save className="size-4" /> Save profile</>}
          </Button>
          {savedProfile && <Badge variant="success"><Check className="size-3" /> Saved</Badge>}
        </div>
      </Card>

      {/* ── Appearance ───────────────────────────────────────────────── */}
      <Card className="p-5 space-y-3">
        <div className="flex items-center gap-2 mb-2"><Palette className="size-4 text-brand-600" /><h2 className="font-semibold">Appearance</h2></div>
        <Field label="Theme">
          <Select value={theme} onChange={(e) => setTheme(e.target.value as any)}>
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </Select>
        </Field>
        <p className="text-xs text-zinc-500">System matches your OS preference and follows changes live.</p>
      </Card>

      {/* ── Password ─────────────────────────────────────────────────── */}
      <Card className="p-5 space-y-3">
        <div className="flex items-center gap-2 mb-2"><Lock className="size-4 text-brand-600" /><h2 className="font-semibold">Change password</h2></div>
        <Field label="Current password">
          <Input type="password" value={pwd.current_password} onChange={(e) => setPwd({ ...pwd, current_password: e.target.value })} />
        </Field>
        <Field label="New password (min 8 chars)">
          <Input type="password" value={pwd.new_password} onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })} />
        </Field>
        {pwdMsg && <p className={pwdMsg.type === "ok" ? "text-sm text-emerald-600" : "text-sm text-rose-600"}>{pwdMsg.text}</p>}
        <Button onClick={changePassword} disabled={!pwd.current_password || pwd.new_password.length < 8}>
          Update password
        </Button>
      </Card>

      {/* ── System settings (admin only) ─────────────────────────────── */}
      {user?.role === "admin" && sys && (
        <Card className="p-5 space-y-3">
          <h2 className="font-semibold">System settings (admin)</h2>
          <ul className="space-y-3">
            {sys.map((s) => (
              <li key={s.key} className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <code className="text-xs font-mono">{s.key}</code>
                  <span className="text-[10px] text-zinc-400">{new Date(s.updated_at).toLocaleString()}</span>
                </div>
                <p className="text-xs text-zinc-500 mb-2">{s.description}</p>
                <div className="flex items-center gap-2">
                  <Input
                    defaultValue={s.value}
                    onBlur={(e) => {
                      if (e.target.value !== s.value) updateSysSetting(s.key, e.target.value);
                    }}
                    className="flex-1"
                  />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Field({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={"block " + (className ?? "")}>
      <span className="text-xs text-zinc-500 block mb-1">{label}</span>
      {children}
    </label>
  );
}
