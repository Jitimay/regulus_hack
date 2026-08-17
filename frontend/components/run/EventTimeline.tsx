"use client";

import { agentLabel, formatDuration, getAgentColor, getStatusColor } from "@/lib/utils";
import type { AgentEvent } from "@/lib/types";
import { useState } from "react";

interface EventTimelineProps {
  events: AgentEvent[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-zinc-600">
        Waiting for events...
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, i) => {
        const isExpanded = expanded.has(event.id);
        const hasMetadata = Object.keys(event.metadata).length > 0;
        const statusColor = getStatusColor(event.status);
        const agentColor = getAgentColor(event.agent);
        const isLast = i === events.length - 1;

        return (
          <div key={event.id} className="group relative pl-8">
            {/* Connector line */}
            {!isLast && (
              <div className="absolute left-3 top-6 bottom-0 w-px bg-zinc-800" />
            )}

            {/* Status dot */}
            <div
              className="absolute left-[9px] top-2.5 h-2.5 w-2.5 rounded-full border-2 border-zinc-950"
              style={{ backgroundColor: statusColor }}
            />

            <div
              className={`rounded border border-zinc-800 bg-zinc-900 p-3 transition-colors ${
                hasMetadata ? "cursor-pointer hover:border-zinc-700" : ""
              }`}
              onClick={() => hasMetadata && toggle(event.id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="text-xs font-medium"
                      style={{ color: agentColor }}
                    >
                      {agentLabel(event.agent)}
                    </span>
                    <span className="text-xs text-zinc-600">·</span>
                    <span className="text-xs text-zinc-500">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    {event.duration_ms != null && (
                      <>
                        <span className="text-xs text-zinc-600">·</span>
                        <span className="text-xs text-zinc-600">
                          {formatDuration(event.duration_ms)}
                        </span>
                      </>
                    )}
                  </div>
                  <p className="mt-0.5 text-sm text-zinc-300">{event.message}</p>
                </div>
                {hasMetadata && (
                  <svg
                    className={`h-3 w-3 flex-shrink-0 text-zinc-600 transition-transform ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                )}
              </div>

              {isExpanded && hasMetadata && (
                <div className="mt-3 rounded border border-zinc-800 bg-zinc-950 p-3">
                  <pre className="text-xs text-zinc-400 overflow-auto max-h-48">
                    {JSON.stringify(event.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
