import type { TicketHistoryEntry } from "../types/triage.ts";

export const TICKET_HISTORY_STORAGE_KEY = "qa_triage_history_v1";
export const MAX_TICKET_HISTORY_ENTRIES = 20;

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function resolveStorage(storage?: StorageLike): StorageLike | null {
  if (storage) {
    return storage;
  }
  if (typeof globalThis !== "undefined" && "localStorage" in globalThis) {
    try {
      return globalThis.localStorage;
    } catch {
      return null;
    }
  }
  return null;
}

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `hist-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function loadTicketHistory(storage?: StorageLike): TicketHistoryEntry[] {
  const store = resolveStorage(storage);
  if (!store) {
    return [];
  }
  try {
    const raw = store.getItem(TICKET_HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(
      (item): item is TicketHistoryEntry =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as TicketHistoryEntry).id === "string" &&
        typeof (item as TicketHistoryEntry).createdAt === "string" &&
        typeof (item as TicketHistoryEntry).ticket === "object"
    );
  } catch {
    return [];
  }
}

export function saveTicketToHistory(
  entry: Omit<TicketHistoryEntry, "id" | "createdAt">,
  storage?: StorageLike
): TicketHistoryEntry[] {
  const store = resolveStorage(storage);
  const current = loadTicketHistory(store ?? undefined);
  const newEntry: TicketHistoryEntry = {
    ...entry,
    id: generateId(),
    createdAt: new Date().toISOString(),
  };
  const updated = [newEntry, ...current].slice(0, MAX_TICKET_HISTORY_ENTRIES);
  if (store) {
    try {
      store.setItem(TICKET_HISTORY_STORAGE_KEY, JSON.stringify(updated));
    } catch {
    }
  }
  return updated;
}

export function deleteTicketFromHistory(
  id: string,
  storage?: StorageLike
): TicketHistoryEntry[] {
  const store = resolveStorage(storage);
  const current = loadTicketHistory(store ?? undefined);
  const updated = current.filter((item) => item.id !== id);
  if (store) {
    try {
      store.setItem(TICKET_HISTORY_STORAGE_KEY, JSON.stringify(updated));
    } catch {
    }
  }
  return updated;
}

export function clearTicketHistory(storage?: StorageLike): TicketHistoryEntry[] {
  const store = resolveStorage(storage);
  if (store) {
    try {
      store.removeItem(TICKET_HISTORY_STORAGE_KEY);
    } catch {
    }
  }
  return [];
}
