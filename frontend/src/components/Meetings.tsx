"use client";

import { useEffect, useState } from "react";
import { CalendarPlus, Link as LinkIcon, MapPin } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Card } from "./Card";

const tabs = ["today", "tomorrow", "week", "upcoming"];

export function Meetings() {
  const [range, setRange] = useState("today");
  const [meetings, setMeetings] = useState<Array<Record<string, string>>>([]);

  useEffect(() => {
    apiGet<{ meetings: Array<Record<string, string>> }>(`/api/meetings?range=${range}`).then((data) => setMeetings(data.meetings ?? [])).catch(() => setMeetings([]));
  }, [range]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-md border border-line bg-white p-1">
          {tabs.map((item) => (
            <button key={item} onClick={() => setRange(item)} className={`rounded px-3 py-2 text-sm capitalize ${range === item ? "bg-brand text-white" : "text-slate-600"}`}>
              {item}
            </button>
          ))}
        </div>
        <button className="flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white">
          <CalendarPlus size={16} />
          Create Meeting
        </button>
      </div>
      <Card title="Meetings">
        <div className="grid gap-3 lg:grid-cols-2">
          {meetings.length ? meetings.map((item) => <MeetingCard key={item.id} item={item} />) : <p className="text-sm text-slate-500">No meetings found for this range.</p>}
        </div>
      </Card>
    </div>
  );
}

function MeetingCard({ item }: { item: Record<string, string> }) {
  return (
    <article className="rounded-lg border border-line p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs text-slate-500">{item.start} - {item.end}</p>
        </div>
        <span className="rounded-full bg-blue-50 px-2 py-1 text-xs text-brand">{item.timezone}</span>
      </div>
      <div className="mt-4 space-y-2 text-xs text-slate-600">
        {item.location && <p className="flex items-center gap-2"><MapPin size={14} />{item.location}</p>}
        {item.meeting_url && <p className="flex items-center gap-2"><LinkIcon size={14} />Meeting link available</p>}
        <p>{Array.isArray(item.attendees) ? item.attendees.length : 0} attendees</p>
      </div>
    </article>
  );
}
