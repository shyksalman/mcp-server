"use client";

import { useEffect, useState } from "react";
import { Bot, ListChecks, MessageSquarePlus, Search } from "lucide-react";
import { apiGet, apiPost, getChatConversationId } from "@/lib/api";

type Conversation = {
  id: string;
  name?: string;
  type: string;
  latest_message?: string;
  latest_timestamp?: string;
  unread_count?: number;
};

type SlackMessage = {
  ts: string;
  datetime?: string;
  user_name?: string;
  text: string;
  thread_ts?: string;
  reply_count?: number;
};

const filters = [
  ["all", "All"],
  ["channels", "Channels"],
  ["dm", "Direct Messages"],
  ["mpim", "Group DMs"]
] as const;

export function Slack() {
  const [filter, setFilter] = useState("all");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<SlackMessage[]>([]);
  const [query, setQuery] = useState("");
  const [composeOpen, setComposeOpen] = useState(false);

  useEffect(() => {
    apiGet<{ conversations: Conversation[] }>(`/api/slack/conversations?filter=${filter}`)
      .then((data) => {
        setConversations(data.conversations ?? []);
        setSelected((current) => current ?? data.conversations?.[0] ?? null);
      })
      .catch(() => setConversations([]));
  }, [filter]);

  useEffect(() => {
    if (!selected) return;
    apiGet<{ messages: SlackMessage[] }>(`/api/slack/messages/${selected.id}?limit=50`)
      .then((data) => setMessages(data.messages ?? []))
      .catch(() => setMessages([]));
  }, [selected]);

  const visible = query ? conversations.filter((item) => (item.name ?? item.id).toLowerCase().includes(query.toLowerCase())) : conversations;

  return (
    <div className="grid h-[calc(100vh-7rem)] overflow-hidden rounded-lg border border-line bg-white shadow-soft lg:grid-cols-[320px_1fr]">
      <aside className="border-b border-line lg:border-b-0 lg:border-r">
        <div className="space-y-3 border-b border-line p-4">
          <button onClick={() => setComposeOpen(true)} className="flex w-full items-center justify-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white">
            <MessageSquarePlus size={16} />
            New Message
          </button>
          <label className="flex items-center gap-2 rounded-md border border-line px-3 py-2">
            <Search size={15} className="text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conversations" className="min-w-0 flex-1 text-sm outline-none" />
          </label>
          <div className="flex flex-wrap gap-2">
            {filters.map(([value, label]) => (
              <button key={value} onClick={() => setFilter(value)} className={`rounded-md px-2 py-1 text-xs ${filter === value ? "bg-blue-50 text-brand" : "bg-slate-100 text-slate-600"}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="max-h-[calc(100vh-20rem)] overflow-y-auto lg:max-h-none">
          {visible.map((item) => (
            <button key={item.id} onClick={() => setSelected(item)} className={`block w-full border-b border-line p-4 text-left ${selected?.id === item.id ? "bg-blue-50" : "hover:bg-slate-50"}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{item.name ?? item.id}</span>
                {!!item.unread_count && <span className="rounded-full bg-brand px-2 py-0.5 text-xs text-white">{item.unread_count}</span>}
              </div>
              <div className="mt-1 text-xs capitalize text-slate-500">{item.type.replace("_", " ")}</div>
              <p className="mt-2 line-clamp-2 text-xs text-slate-500">{item.latest_message ?? "No recent preview available"}</p>
            </button>
          ))}
        </div>
      </aside>
      <section className="flex min-h-0 flex-col">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold">{selected?.name ?? selected?.id ?? "Slack"}</h2>
            <p className="text-xs text-slate-500">Conversation and thread context available to the Slack app</p>
          </div>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs text-slate-600">
              <Bot size={14} />
              Summarize Thread
            </button>
            <button className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-xs text-slate-600">
              <ListChecks size={14} />
              Action Items
            </button>
          </div>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto p-5">
          {messages.length ? messages.map((message) => <MessageBubble key={message.ts} message={message} />) : <p className="rounded-md border border-dashed border-line p-5 text-sm text-slate-500">No messages loaded, or the Slack app cannot access this conversation.</p>}
        </div>
        <div className="border-t border-line p-4">
          <p className="rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-500">Use AI Assistant to send messages with confirmation, or search and summarize Slack context naturally.</p>
        </div>
      </section>
      {composeOpen && <ComposeModal onClose={() => setComposeOpen(false)} />}
    </div>
  );
}

function MessageBubble({ message }: { message: SlackMessage }) {
  return (
    <article className="rounded-lg border border-line p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm font-medium">{message.user_name ?? "Slack"}</div>
        <div className="text-xs text-slate-400">{message.datetime ?? message.ts}</div>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{message.text}</p>
      {!!message.reply_count && <div className="mt-3 text-xs text-brand">{message.reply_count} replies</div>}
    </article>
  );
}

function ComposeModal({ onClose }: { onClose: () => void }) {
  const [recipients, setRecipients] = useState("");
  const [mode, setMode] = useState<"individual" | "group">("individual");
  const [message, setMessage] = useState("");
  const count = recipients.split(",").map((item) => item.trim()).filter(Boolean).length;

  async function prepare() {
    const prompt = `Prepare a Slack ${mode === "individual" ? "individual DM" : "group DM"} to ${recipients}: ${message}`;
    await apiPost("/api/chat", { message: prompt, conversation_id: getChatConversationId() }).catch(() => undefined);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/30 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-soft">
        <h3 className="text-sm font-semibold">New Slack Message</h3>
        <div className="mt-4 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-slate-500">Recipients</span>
            <input value={recipients} onChange={(event) => setRecipients(event.target.value)} placeholder="Ali, Ahmed, Waqas" className="w-full rounded-md border border-line px-3 py-2 outline-none focus:border-brand" />
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            <button onClick={() => setMode("individual")} className={`rounded-md border px-3 py-2 text-left text-sm ${mode === "individual" ? "border-brand bg-blue-50 text-brand" : "border-line"}`}>Individual DM</button>
            <button onClick={() => setMode("group")} className={`rounded-md border px-3 py-2 text-left text-sm ${mode === "group" ? "border-brand bg-blue-50 text-brand" : "border-line"}`}>Group DM</button>
          </div>
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-slate-500">Message</span>
            <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={5} className="w-full rounded-md border border-line px-3 py-2 outline-none focus:border-brand" />
          </label>
          <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
            {mode === "individual" ? `This will prepare ${count} separate message${count === 1 ? "" : "s"}.` : "This will prepare one shared group conversation."}
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-line px-4 py-2 text-sm">Cancel</button>
          <button onClick={prepare} className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white">Preview</button>
        </div>
      </div>
    </div>
  );
}
