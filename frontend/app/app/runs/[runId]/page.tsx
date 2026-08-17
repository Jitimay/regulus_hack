"use client";

import { use } from "react";
import Link from "next/link";
import { useRun, useRunEvents } from "@/hooks/useRun";
import { RunStatusBar } from "@/components/run/RunStatusBar";
import { EventTimeline } from "@/components/run/EventTimeline";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { isTerminal, isRunning, formatUSD, interventionLabel } from "@/lib/utils";

interface Params {
  params: Promise<{ runId: string }>;
}

export default function RunPage({ params }: Params) {
  const { runId } = use(params);
  const { data: run, isLoading: runLoading, error: runError } = useRun(runId);
  const running = run ? isRunning(run.status) : false;
  const { data: events = [] } = useRunEvents(runId, running || !isTerminal(run?.status ?? "created"));

  if (runLoading) {
    return <RunSkeleton />;
  }

  if (runError || !run) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">Run not found or failed to load.</p>
          <Link href="/app/new"><Button variant="secondary">New scenario</Button></Link>
        </div>
      </div>
    );
  }

  const completed = run.status === "completed";

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-indigo-600">
                <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span className="font-semibold text-sm tracking-tight text-zinc-100">Regulus</span>
            </Link>
            <span className="text-zinc-700">/</span>
            <span className="text-sm text-zinc-500 font-mono">{runId.slice(0, 8)}…</span>
          </div>
          <div className="flex items-center gap-2">
            {completed && (
              <>
                <Link href={`/app/model/${runId}`}>
                  <Button variant="secondary" size="sm">View Model</Button>
                </Link>
                <Link href={`/app/results/${runId}`}>
                  <Button size="sm">View Results</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6">
          <h1 className="mb-1 text-xl font-bold text-zinc-100 line-clamp-2">
            {run.input.decision_question}
          </h1>
          <p className="text-sm text-zinc-500">
            {formatUSD(run.input.budget_usd)} budget ·{" "}
            {run.input.communities.map((c) => c.name).join(", ")} ·{" "}
            Started {new Date(run.created_at).toLocaleString()}
          </p>
        </div>

        {/* Status bar */}
        <div className="mb-6">
          <RunStatusBar status={run.status} researchLoops={run.research_loop_count} />
        </div>

        {run.status === "failed" && run.error_message && (
          <div className="mb-6 rounded border border-red-800 bg-red-950/30 p-4">
            <p className="text-sm font-medium text-red-400">Run failed</p>
            <p className="mt-1 text-xs text-red-500">{run.error_message}</p>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Event timeline — main column */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Agent Execution Log</CardTitle>
                <span className="text-xs text-zinc-600">{events.length} events</span>
              </CardHeader>
              <EventTimeline events={events} />
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Run Details</CardTitle>
              </CardHeader>
              <dl className="space-y-3">
                <Detail label="Status" value={<Badge variant={run.status === "completed" ? "success" : run.status === "failed" ? "error" : "info"}>{run.status}</Badge>} />
                <Detail label="Budget" value={formatUSD(run.input.budget_usd)} />
                <Detail label="Research loops" value={String(run.research_loop_count)} />
                {run.input.communities.length > 0 && (
                  <Detail
                    label="Communities"
                    value={run.input.communities.map((c) => c.name).join(", ")}
                  />
                )}
              </dl>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Scenarios</CardTitle>
              </CardHeader>
              <div className="space-y-1.5">
                {run.input.interventions.map((intervention) => (
                  <div key={intervention} className="flex items-center gap-2 text-sm">
                    <div className="h-1.5 w-1.5 rounded-full bg-zinc-600" />
                    <span className="text-zinc-400">{interventionLabel(intervention)}</span>
                  </div>
                ))}
              </div>
            </Card>

            {completed && (
              <div className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-4">
                <p className="text-sm font-medium text-emerald-400 mb-3">Analysis complete</p>
                <div className="space-y-2">
                  <Link href={`/app/model/${runId}`} className="block">
                    <Button variant="secondary" size="sm" className="w-full justify-start">
                      View probabilistic model →
                    </Button>
                  </Link>
                  <Link href={`/app/results/${runId}`} className="block">
                    <Button size="sm" className="w-full justify-start">
                      View recommendation →
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <dt className="text-xs text-zinc-600">{label}</dt>
      <dd className="text-xs text-zinc-300 text-right">{value}</dd>
    </div>
  );
}

function RunSkeleton() {
  return (
    <div className="min-h-screen bg-zinc-950 animate-pulse">
      <div className="h-14 border-b border-zinc-800 bg-zinc-900" />
      <div className="mx-auto max-w-7xl px-6 py-8 space-y-4">
        <div className="h-8 w-2/3 rounded bg-zinc-800" />
        <div className="h-4 w-1/3 rounded bg-zinc-800" />
        <div className="h-24 rounded bg-zinc-900 border border-zinc-800" />
      </div>
    </div>
  );
}
