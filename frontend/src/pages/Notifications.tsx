import { useEffect } from "react";
import { Bell, Check, Trash } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useNotificationStore } from "@/store/notifications";
import type { NotificationType } from "@/types";

const variantOf: Record<NotificationType, "default" | "success" | "warning" | "danger" | "info"> = {
  info: "info", success: "success", warning: "warning", error: "danger", system: "default"
};

export default function NotificationsPage() {
  const { items, fetch, markRead, markAllRead, remove, loading } = useNotificationStore();

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2"><Bell className="size-6" /> Notifications</h1>
        <Button variant="outline" onClick={markAllRead}><Check className="size-4" /> Mark all read</Button>
      </div>

      {loading && items.length === 0 ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : items.length === 0 ? (
        <Card className="p-8 text-center text-sm text-zinc-500">No notifications yet.</Card>
      ) : (
        <ul className="space-y-2">
          {items.map((n) => (
            <li key={n.id}>
              <Card className={"p-4 " + (n.read ? "opacity-70" : "")}>
                <div className="flex items-start gap-3">
                  <Badge variant={variantOf[n.type]}>{n.type}</Badge>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold">{n.title}</div>
                    <p className="text-sm text-zinc-600 dark:text-zinc-300 whitespace-pre-wrap">{n.message}</p>
                    <div className="text-[10px] text-zinc-400 mt-2">{new Date(n.created_at).toLocaleString()}</div>
                  </div>
                  <div className="flex gap-1">
                    {!n.read && (
                      <button onClick={() => markRead(n.id)} title="Mark as read" className="p-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800">
                        <Check className="size-4" />
                      </button>
                    )}
                    <button onClick={() => remove(n.id)} title="Delete" className="p-2 rounded hover:bg-rose-500/10 text-rose-500">
                      <Trash className="size-4" />
                    </button>
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
