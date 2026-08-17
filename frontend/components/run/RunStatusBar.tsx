"use client";

import { runStatusLabel, isTerminal } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { RunStatus } from "@/lib/types";

const STATUS_STEPS: RunStatus[] = [
  "planning",
  "researching",
  "modeling",
  "simulating",
  "analyzing",
  "researching_again",
  "finalizing",
  "completed",
];

interface RunStatusBarProps {
  status: RunStatus;
  researchLoops: number;
}

export function RunStatusBar({ status, researchLoops }: RunStatusBarProps) {
  const variant =
    status === "completed"
      ? "success"
      : status === "failed"
        ? "error"
        : status === "cancelled"
          ? "outline"
          : "info";

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {!isTerminal(status) && (
            <div className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
          )}
          <span className="text-sm font-medium text-zinc-200">
            {runStatusLabel(status)}
          </span>
          <Badge variant={variant}>{status}</Badge>
        </div>
        {researchLoops > 1 && (
          <Badge variant="warning">
            {researchLoops} research loops
          </Badge>
        )}
      </div>

      {/* Step progress */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_STEPS.map((step) => {
          const stepIdx = STATUS_STEPS.indexOf(step);
          const currentIdx = STATUS_STEPS.indexOf(status as RunStatus);
          const isDone = currentIdx > stepIdx || status === "completed";
          const isCurrent = step === status;
          const isSkipped = step === "researching_again" && researchLoops <= 1 && !isCurrent && !isDone;

          if (isSkipped) return null;

          return (
            <div
              key={step}
              className={`flex items-center gap-1.5 rounded px-2 py-1 text-xs transition-colors ${
                isDone
                  ? "bg-emerald-950 text-emerald-400"
                  : isCurrent
                    ? "bg-indigo-950 text-indigo-300"
                    : "bg-zinc-800 text-zinc-600"
              }`}
            >
              {isDone ? (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : isCurrent ? (
                <div className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              ) : (
                <div className="h-2 w-2 rounded-full bg-zinc-600" />
              )}
              {runStatusLabel(step)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
