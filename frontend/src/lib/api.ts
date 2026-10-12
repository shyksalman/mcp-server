function apiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (typeof window === "undefined") {
    return configured ?? "http://localhost:8000";
  }
  const host = window.location.hostname;
  const isLocalPage = host === "localhost" || host === "127.0.0.1";
  const configuredIsLocalhost = configured?.includes("localhost") || configured?.includes("127.0.0.1");
  if (configured && !(configuredIsLocalhost && !isLocalPage)) {
    return configured;
  }
  return `${window.location.protocol}//${host}:8000`;
}

const conversationStorageKey = "employee-copilot-conversation-id";

export function createChatConversationId(): string {
  if (typeof window.crypto?.randomUUID === "function") {
    return window.crypto.randomUUID();
  }

  const bytes = new Uint8Array(16);
  if (typeof window.crypto?.getRandomValues === "function") {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}

export function getChatConversationId(): string {
  const stored = window.localStorage.getItem(conversationStorageKey);
  if (stored) return stored;
  const created = createChatConversationId();
  window.localStorage.setItem(conversationStorageKey, created);
  return created;
}

export function setChatConversationId(conversationId: string): void {
  window.localStorage.setItem(conversationStorageKey, conversationId);
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${apiBase()}${path}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await response.text());
}
