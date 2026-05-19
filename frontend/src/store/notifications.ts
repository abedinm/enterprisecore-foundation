// Notifications store — polled from /api/v1/notifications.

import { create } from "zustand";
import { api } from "@/api/client";
import type { Notification } from "@/types";

interface NotifState {
  items: Notification[];
  unread: number;
  loading: boolean;
  fetch: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  remove: (id: number) => Promise<void>;
}

export const useNotificationStore = create<NotifState>((set, get) => ({
  items: [],
  unread: 0,
  loading: false,
  fetch: async () => {
    set({ loading: true });
    try {
      const r = await api.get<Notification[]>("/notifications", { params: { limit: 30 } });
      const items = r.data;
      const unread = items.filter((n) => !n.read).length;
      set({ items, unread });
    } finally {
      set({ loading: false });
    }
  },
  markRead: async (id) => {
    await api.post(`/notifications/${id}/read`);
    set({ items: get().items.map((n) => (n.id === id ? { ...n, read: true } : n)) });
    set({ unread: get().items.filter((n) => !n.read).length });
  },
  markAllRead: async () => {
    await api.post(`/notifications/read-all`);
    set({ items: get().items.map((n) => ({ ...n, read: true })), unread: 0 });
  },
  remove: async (id) => {
    await api.delete(`/notifications/${id}`);
    set({ items: get().items.filter((n) => n.id !== id) });
    set({ unread: get().items.filter((n) => !n.read).length });
  }
}));
