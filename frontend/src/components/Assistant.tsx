"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Send, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPost, createChatConversationId, getChatConversationId, setChatConversationId } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };
type ChatResponse = { message: string; conversation_id: string };

const suggestions = [
  "What meetings do I have today?",
  "Show my urgent ClickUp tickets.",
  "How is my attendance this month?",
  "What should I focus on today?",
  "Do I have any pending leave?"
];

export function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const storedId = window.localStorage.getItem("employee-copilot-conversation-id");
    const id = getChatConversationId();
    setConversationId(id);
    if (storedId) {
      apiGet<{ messages: Message[] }>(`/api/chat/${id}`)
        .then((history) => {
          if (active) setMessages(history.messages);
        })
        .catch(() => undefined);
    }
    return () => {
      active = false;
    };
  }, []);

  async function submit(text = input) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setInput("");
    setLoading(true);
    setMessages((items) => [...items, { role: "user", content: trimmed }]);
    try {
      const id = conversationId ?? getChatConversationId();
      if (!conversationId) {
        setConversationId(id);
      }
      const response = await apiPost<ChatResponse>("/api/chat", { message: trimmed, conversation_id: id });
      if (response.conversation_id !== id) {
        setConversationId(response.conversation_id);
        setChatConversationId(response.conversation_id);
      }
      setMessages((items) => [...items, { role: "assistant", content: response.message }]);
    } catch {
      setMessages((items) => [...items, { role: "assistant", content: "I could not reach the copilot backend right now." }]);
    } finally {
      setLoading(false);
    }
  }

  async function clearConversation() {
    if (loading) return;
    const oldId = conversationId;
    const newId = createChatConversationId();
    setMessages([]);
    setConversationId(newId);
    setChatConversationId(newId);
    if (oldId) await apiDelete(`/api/chat/${oldId}`).catch(() => undefined);
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col rounded-lg border border-line bg-white shadow-soft">
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <div>
          <h2 className="text-sm font-semibold">Employee AI Copilot</h2>
          <p className="text-xs text-slate-500">{loading ? "Checking your tools..." : "Ask naturally about OMS, meetings, and ClickUp"}</p>
        </div>
        <button disabled={loading} onClick={clearConversation} className="grid size-9 place-items-center rounded-md border border-line text-slate-500 disabled:opacity-50" aria-label="Clear conversation">
          <Trash2 size={16} />
        </button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {!messages.length && (
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestions.map((item) => (
              <button key={item} onClick={() => submit(item)} className="rounded-md border border-line p-4 text-left text-sm hover:border-brand hover:text-brand">
                {item}
              </button>
            ))}
          </div>
        )}
        {messages.map((item, index) => (
          <div key={index} className={`flex ${item.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-3xl rounded-lg px-4 py-3 text-sm ${item.role === "user" ? "bg-brand text-white" : "bg-slate-100 text-ink"}`}>
              <ReactMarkdown className="prose prose-sm max-w-none">{item.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-slate-500">Checking calendar, ClickUp, or OMS as needed...</div>}
      </div>
      <form
        className="flex gap-3 border-t border-line p-4"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about attendance, meetings, leaves or ClickUp..."
          className="min-w-0 flex-1 rounded-md border border-line px-4 py-3 text-sm outline-none focus:border-brand"
        />
        <button className="grid size-12 place-items-center rounded-md bg-brand text-white" aria-label="Send message">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
