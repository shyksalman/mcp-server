"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { apiGet } from "@/lib/api";

const filters = ["all", "open", "in_progress", "high_priority", "due_today", "overdue", "completed"];

export function ClickUp() {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [tasks, setTasks] = useState<Array<Record<string, string>>>([]);

  useEffect(() => {
    const params = new URLSearchParams({ filter });
    if (search) params.set("search", search);
    apiGet<{ tasks: Array<Record<string, string>> }>(`/api/tasks?${params.toString()}`).then((data) => setTasks(data.tasks ?? [])).catch(() => setTasks([]));
  }, [filter, search]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 rounded-lg border border-line bg-white p-4 shadow-soft lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {filters.map((item) => (
            <button key={item} onClick={() => setFilter(item)} className={`rounded-md px-3 py-2 text-xs capitalize ${filter === item ? "bg-brand text-white" : "bg-slate-100 text-slate-600"}`}>
              {item.replace("_", " ")}
            </button>
          ))}
        </div>
        <label className="flex min-w-64 items-center gap-2 rounded-md border border-line px-3 py-2">
          <Search size={16} className="text-slate-400" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search tasks" className="min-w-0 flex-1 text-sm outline-none" />
        </label>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {tasks.length ? tasks.map((task) => <TaskCard key={task.id} task={task} />) : <div className="rounded-lg border border-line bg-white p-6 text-sm text-slate-500">No ClickUp tasks match this view.</div>}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Record<string, string> }) {
  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{task.name}</h3>
          <p className="mt-1 text-xs text-slate-500">{task.project ?? task.list ?? "ClickUp"} · {task.status ?? "Open"}</p>
        </div>
        {task.url && <a href={task.url} target="_blank" className="text-slate-400" aria-label="Open in ClickUp"><ExternalLink size={16} /></a>}
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-slate-100 px-2 py-1">{task.priority ?? "Normal"}</span>
        <span className="rounded-full bg-slate-100 px-2 py-1">{task.due_date ?? "No due date"}</span>
      </div>
    </article>
  );
}
