"use client";

import { use } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { useRunResults } from "@/hooks/useRun";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatPct,
  formatUSD,
  formatNumber,
  interventionLabel,
  confidenceLabel,
} from "@/lib/utils";
import type { ScenarioResult, SensitivityEntry } from "@/lib/types";

interface Params {
  params: Promise<{ runId: string }>;
}

export default function ResultsPage({ params }: Params) {
  const { runId } = use(params);
  const { data: result, isLoading, error } = useRunResults(runId, true);

  if (isLoading) {
    return <ResultsSkeleton />;
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-2">Results not yet available.</p>
          <p className="text-sm text-zinc-600 mb-4">The run may still be executing.</p>
          <Link href={`/app/runs/${runId}`}>
            <Button variant="secondary">Check run status</Button>
          </Link>
        </div>
      </div>
    );
  }

  const { recommendation: rec, scenario_results: scenarios, sensitivity } = result;

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
            <span className="text-sm text-zinc-400">Results</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href={`/app/scenarios/${runId}`}>
              <Button variant="secondary" size="sm">Scenarios</Button>
            </Link>
            <Link href={`/app/model/${runId}`}>
              <Button variant="secondary" size="sm">View Model</Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {/* Disclaimer */}
        <div className="rounded border border-amber-800/50 bg-amber-950/20 px-4 py-2.5">
          <p className="text-xs text-amber-600">
            <strong className="text-amber-500">Scenario estimates only.</strong>{" "}
            Results are based on probabilistic simulation using {result.research_loop_count} research loop(s).
            All values carry uncertainty. Consult domain experts before making real decisions.
          </p>
        </div>

        {/* Recommendation */}
        {rec && (
          <section>
            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">
                Recommendation
              </p>
              <div className="rounded-lg border border-emerald-800 bg-emerald-950/20 p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h1 className="text-2xl font-bold text-emerald-400">
                      {interventionLabel(rec.recommended_scenario_name)}
                    </h1>
                    <p className="mt-1 text-sm text-zinc-400">
                      Under current model assumptions
                    </p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-zinc-100">
                        {formatPct(rec.confidence)}
                      </div>
                      <div className="text-xs text-zinc-500">Confidence</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-zinc-100">
                        {formatPct(rec.robustness)}
                      </div>
                      <div className="text-xs text-zinc-500">Robustness</div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-3 mb-4">
                  <Metric
                    label="Expected access improvement"
                    value={formatPct(rec.expected_impact)}
                    sub="mean estimate"
                  />
                  <Metric
                    label="Estimated households served"
                    value={formatNumber(rec.expected_households_served)}
                    sub="under this scenario"
                  />
                  <Metric
                    label="Budget"
                    value={formatUSD(rec.cost_usd)}
                    sub="full allocation"
                  />
                </div>

                <p className="text-sm text-zinc-300 leading-relaxed">{rec.summary}</p>
              </div>
            </div>
          </section>
        )}

        {/* Scenario comparison chart */}
        <section>
          <Card>
            <CardHeader>
              <CardTitle>Scenario Comparison</CardTitle>
            </CardHeader>
            <ScenarioComparisonChart scenarios={scenarios} />
          </Card>
        </section>

        {/* Sensitivity */}
        {sensitivity && sensitivity.entries.length > 0 && (
          <section>
            <Card>
              <CardHeader>
                <CardTitle>Sensitivity Analysis</CardTitle>
                <span className="text-xs text-zinc-600">
                  Variables with highest influence on outcome
                </span>
              </CardHeader>
              <SensitivityChart entries={sensitivity.entries.slice(0, 7)} />
              {sensitivity.dominant_variable && (
                <div className="mt-4 rounded border border-amber-800/40 bg-amber-950/20 p-3">
                  <p className="text-xs text-amber-500">
                    <strong>Dominant uncertainty:</strong>{" "}
                    <span className="font-mono">{sensitivity.dominant_variable}</span>{" "}
                    (score {sensitivity.dominant_uncertainty_score.toFixed(2)}).
                    {sensitivity.is_material
                      ? " Material — an additional research loop was triggered."
                      : " Resolved — uncertainty was below the materiality threshold."}
                  </p>
                </div>
              )}
            </Card>
          </section>
        )}

        {/* Full reasoning */}
        {rec && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Why this recommendation</CardTitle></CardHeader>
              <p className="text-sm text-zinc-400 leading-relaxed">{rec.reasoning}</p>
            </Card>

            <Card>
              <CardHeader><CardTitle>Uncertainty notes</CardTitle></CardHeader>
              <p className="text-sm text-zinc-400 leading-relaxed mb-4">{rec.uncertainty_notes}</p>
              {rec.sensitive_variables.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {rec.sensitive_variables.map((v) => (
                    <Badge key={v} variant="outline" className="font-mono">{v}</Badge>
                  ))}
                </div>
              )}
            </Card>

            <Card>
              <CardHeader><CardTitle>Key risks</CardTitle></CardHeader>
              <ul className="space-y-2">
                {rec.key_risks.map((risk, i) => (
                  <li key={i} className="flex gap-2 text-sm text-zinc-400">
                    <span className="text-red-500 mt-0.5 flex-shrink-0">▲</span>
                    {risk}
                  </li>
                ))}
              </ul>
            </Card>

            <Card>
              <CardHeader><CardTitle>Key assumptions</CardTitle></CardHeader>
              <ul className="space-y-2">
                {rec.key_assumptions.map((assumption, i) => (
                  <li key={i} className="flex gap-2 text-sm text-zinc-400">
                    <span className="text-amber-500 mt-0.5 flex-shrink-0">◆</span>
                    {assumption}
                  </li>
                ))}
              </ul>
            </Card>

            {rec.conditions_for_change.length > 0 && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>What would change this recommendation</CardTitle>
                  <span className="text-xs text-zinc-600">Conditions under which a different intervention becomes preferable</span>
                </CardHeader>
                <ul className="space-y-2">
                  {rec.conditions_for_change.map((condition, i) => (
                    <li key={i} className="flex gap-2 text-sm text-zinc-400">
                      <span className="text-indigo-500 mt-0.5 flex-shrink-0">◇</span>
                      {condition}
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {rec.alternative_comparisons.length > 0 && (
              <Card className="lg:col-span-2">
                <CardHeader><CardTitle>Alternative scenarios</CardTitle></CardHeader>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-zinc-800">
                        <th className="pb-2 text-left text-zinc-500">Scenario</th>
                        <th className="pb-2 text-left text-zinc-500">Expected impact</th>
                        <th className="pb-2 text-left text-zinc-500">Why not recommended</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rec.alternative_comparisons.map((alt) => (
                        <tr key={alt.scenario_name} className="border-b border-zinc-800/50">
                          <td className="py-2 pr-4 font-medium text-zinc-300">
                            {interventionLabel(alt.scenario_name)}
                          </td>
                          <td className="py-2 pr-4 text-zinc-400">
                            {formatPct(alt.expected_impact)}
                          </td>
                          <td className="py-2 text-zinc-500">{alt.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        )}

        <div className="flex justify-end pt-4">
          <Link href="/app/new">
            <Button variant="secondary">New scenario →</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart components
// ---------------------------------------------------------------------------

function ScenarioComparisonChart({ scenarios }: { scenarios: ScenarioResult[] }) {
  const sorted = [...scenarios].sort((a, b) => a.rank - b.rank);
  const data = sorted.map((s) => ({
    name: interventionLabel(s.scenario_name).replace(" Strategy", "").replace(" Expansion", " Exp."),
    impact: Number((s.access_improvement.mean * 100).toFixed(1)),
    robustness: Number((s.robustness * 100).toFixed(1)),
    p10: Number((s.access_improvement.p10 * 100).toFixed(1)),
    rank: s.rank,
  }));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-zinc-500 mb-3">Expected access improvement (%) — mean ± downside</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} unit="%" />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px" }}
              labelStyle={{ color: "#e4e4e7" }}
              itemStyle={{ color: "#a1a1aa" }}
            />
            <ReferenceLine y={0} stroke="#3f3f46" />
            <Bar dataKey="impact" name="Expected improvement" radius={[3, 3, 0, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.rank === 1 ? "#10b981" : "#6366f1"}
                  opacity={entry.rank === 1 ? 1 : 0.6}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="text-xs text-zinc-500 mb-3">Robustness — P(outcome ≥ target) (%)</p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
            <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} unit="%" domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px" }}
              labelStyle={{ color: "#e4e4e7" }}
              itemStyle={{ color: "#a1a1aa" }}
            />
            <Bar dataKey="robustness" name="Robustness" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function SensitivityChart({ entries }: { entries: SensitivityEntry[] }) {
  const data = entries.map((e) => ({
    name: e.variable_name.replace(/_/g, " "),
    score: Number((e.sensitivity_score * 100).toFixed(1)),
    direction: e.direction,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
        <XAxis type="number" tick={{ fill: "#a1a1aa", fontSize: 11 }} unit="%" domain={[0, 100]} />
        <YAxis type="category" dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} width={140} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px" }}
          labelStyle={{ color: "#e4e4e7" }}
          itemStyle={{ color: "#a1a1aa" }}
          formatter={(v) => [`${v}%`, "Sensitivity score"]}
        />
        <Bar dataKey="score" name="Sensitivity" radius={[0, 3, 3, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={entry.direction === "positive" ? "#6366f1" : "#ef4444"}
              opacity={0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-zinc-100">{value}</div>
      {sub && <div className="text-xs text-zinc-600 mt-0.5">{sub}</div>}
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="min-h-screen bg-zinc-950 animate-pulse">
      <div className="h-14 border-b border-zinc-800 bg-zinc-900" />
      <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <div className="h-48 rounded-lg bg-zinc-800" />
        <div className="h-64 rounded-lg bg-zinc-800" />
      </div>
    </div>
  );
}
