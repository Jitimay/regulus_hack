"use client";

import { use } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRunModel } from "@/hooks/useRun";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatPct } from "@/lib/utils";

// Dynamic import so ReactFlow doesn't break SSR
const PGMGraph = dynamic(
  () => import("@/components/model/PGMGraph").then((m) => m.PGMGraph),
  { ssr: false, loading: () => <div className="h-96 flex items-center justify-center text-sm text-zinc-600">Loading graph...</div> }
);

interface Params {
  params: Promise<{ runId: string }>;
}

export default function ModelPage({ params }: Params) {
  const { runId } = use(params);
  const { data: model, isLoading, error } = useRunModel(runId, true);

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="font-semibold text-sm text-zinc-100">Regulus</Link>
            <span className="text-zinc-700">/</span>
            <Link href={`/app/runs/${runId}`} className="text-sm text-zinc-500 hover:text-zinc-300">
              {runId.slice(0, 8)}…
            </Link>
            <span className="text-zinc-700">/</span>
            <span className="text-sm text-zinc-400">Model</span>
          </div>
          <Link href={`/app/results/${runId}`}>
            <Button size="sm">View Results →</Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-zinc-100 mb-1">Probabilistic Graphical Model</h1>
          <p className="text-sm text-zinc-500">
            Bayesian network representing causal relationships between infrastructure variables.
            Click a node to inspect its parameters.
          </p>
        </div>

        {isLoading && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 h-96 flex items-center justify-center">
            <p className="text-sm text-zinc-600 animate-pulse">Loading model...</p>
          </div>
        )}

        {error && (
          <div className="rounded border border-red-800 bg-red-950/30 p-4">
            <p className="text-sm text-red-400">Model not yet available. The run may still be executing.</p>
          </div>
        )}

        {model && (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Nodes" value={String(model.node_count)} />
              <Stat label="Edges" value={String(model.edge_count)} />
              {model.research_loop != null && (
                <Stat label="Research loop" value={String(model.research_loop)} />
              )}
            </div>

            {/* Main graph */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 overflow-hidden" style={{ height: 560 }}>
              <PGMGraph model={model} />
            </div>

            {/* Node table */}
            <Card>
              <CardHeader>
                <CardTitle>Node Parameters</CardTitle>
              </CardHeader>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="pb-2 text-left text-zinc-500 font-medium">Variable</th>
                      <th className="pb-2 text-left text-zinc-500 font-medium">Type</th>
                      <th className="pb-2 text-left text-zinc-500 font-medium">Confidence</th>
                      <th className="pb-2 text-left text-zinc-500 font-medium">Status</th>
                      <th className="pb-2 text-left text-zinc-500 font-medium">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {model.nodes.map((node) => (
                      <tr key={node.name} className="border-b border-zinc-800/50">
                        <td className="py-2 pr-4">
                          <div className="font-medium text-zinc-200">{node.display_name}</div>
                          <div className="text-zinc-600">{node.unit}</div>
                        </td>
                        <td className="py-2 pr-4 text-zinc-400">{node.distribution.type}</td>
                        <td className="py-2 pr-4">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 rounded-full bg-zinc-800">
                              <div
                                className="h-full rounded-full bg-indigo-500"
                                style={{ width: `${node.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-zinc-400">{formatPct(node.confidence)}</span>
                          </div>
                        </td>
                        <td className="py-2 pr-4">
                          <Badge
                            variant={
                              node.evidence_status === "external_evidence"
                                ? "success"
                                : node.evidence_status === "inferred"
                                  ? "info"
                                  : "outline"
                            }
                          >
                            {node.evidence_status}
                          </Badge>
                        </td>
                        <td className="py-2 text-zinc-500 max-w-xs truncate">{node.evidence_source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-zinc-100">{value}</div>
    </div>
  );
}
