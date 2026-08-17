"use client";

import { use } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Legend,
} from "recharts";
import { useRunResults } from "@/hooks/useRun";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatPct, formatUSD, formatNumber, interventionLabel } from "@/lib/utils";
import type { ScenarioResult } from "@/lib/types";

interface Params { params: Promise<{ runId: string }> }

const COLORS = ["#10b981", "#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b"];

export default function ScenariosPage({ params }: Params) {
  const { runId } = use(params);
  const { data: result, isLoading, error } = useRunResults(runId, true);

  if (isLoading) return <Skeleton />;

  if (error || !result) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-2">Results not yet available.</p>
          <Link href={`/app/runs/${runId}`}><Button variant="secondary">Check run status</Button></Link>
        </div>
      </div>
    );
  }

  const scenarios = [...result.scenario_results].sort((a, b) => a.rank - b.rank);
  const best = scenarios[0];

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="font-semibold text-sm text-zinc-100">Regulus</Link>
            <span className="text-zinc-700">/</span>
            <Link href={`/app/runs/${runId}`} className="text-sm text-zinc-500 hover:text-zinc-300">{runId.slice(0, 8)}…</Link>
            <span className="text-zinc-700">/</span>
            <span className="text-sm text-zinc-400">Scenarios</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href={`/app/model/${runId}`}><Button variant="secondary" size="sm">View Model</Button></Link>
            <Link href={`/app/results/${runId}`}><Button size="sm">View Results</Button></Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">Scenario Comparison</p>
          <h1 className="text-xl font-bold text-zinc-100">
            {scenarios.length} intervention scenarios evaluated
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Ranked by composite score: 50% expected impact · 30% robustness · 20% downside protection
          </p>
        </div>

        {/* Ranking table */}
        <Card>
          <CardHeader><CardTitle>Scenario Rankings</CardTitle></CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  {["Rank", "Scenario", "Expected Impact", "Robustness", "P10 (downside)", "Households", "Cost"].map(h => (
                    <th key={h} className="pb-3 text-left text-xs text-zinc-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s, i) => (
                  <tr key={s.scenario_id} className="border-b border-zinc-800/50">
                    <td className="py-3 pr-4">
                      <span className={`inline-flex h-6 w-6 items-center justify-center rounded text-xs font-bold ${i === 0 ? "bg-emerald-900 text-emerald-300" : "bg-zinc-800 text-zinc-400"}`}>
                        {s.rank}
                      </span>
                    </td>
                    <td className="py-3 pr-4 font-medium text-zinc-200">
                      {interventionLabel(s.scenario_name)}
                      {i === 0 && <Badge variant="success" className="ml-2 text-xs">Recommended</Badge>}
                    </td>
                    <td className="py-3 pr-4 text-zinc-300">{formatPct(s.access_improvement.mean)}</td>
                    <td className="py-3 pr-4 text-zinc-300">{formatPct(s.robustness)}</td>
                    <td className={`py-3 pr-4 ${s.access_improvement.p10 < 0 ? "text-red-400" : "text-zinc-300"}`}>
                      {formatPct(s.access_improvement.p10)}
                    </td>
                    <td className="py-3 pr-4 text-zinc-300">{formatNumber(s.expected_households_served)}</td>
                    <td className="py-3 text-zinc-400">{formatUSD(s.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Charts row */}
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Expected Access Improvement</CardTitle>
              <span className="text-xs text-zinc-600">Mean outcome — higher is better</span>
            </CardHeader>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scenarios.map((s, i) => ({
                name: interventionLabel(s.scenario_name).replace(" Strategy", "").replace(" Expansion", " Exp."),
                value: Number((s.access_improvement.mean * 100).toFixed(1)),
                rank: s.rank,
                color: COLORS[i % COLORS.length],
              }))} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} unit="%" />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px" }} labelStyle={{ color: "#e4e4e7" }} itemStyle={{ color: "#a1a1aa" }} />
                <Bar dataKey="value" name="Impact" radius={[3, 3, 0, 0]}>
                  {scenarios.map((s, i) => (
                    <Cell key={s.scenario_id} fill={COLORS[i % COLORS.length]} opacity={s.rank === 1 ? 1 : 0.55} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Robustness</CardTitle>
              <span className="text-xs text-zinc-600">P(outcome ≥ target) — higher is more reliable</span>
            </CardHeader>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scenarios.map((s, i) => ({
                name: interventionLabel(s.scenario_name).replace(" Strategy", "").replace(" Expansion", " Exp."),
                value: Number((s.robustness * 100).toFixed(1)),
                color: COLORS[i % COLORS.length],
              }))} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="name" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                <YAxis tick={{ fill: "#a1a1aa", fontSize: 11 }} unit="%" domain={[0, 100]} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px" }} labelStyle={{ color: "#e4e4e7" }} itemStyle={{ color: "#a1a1aa" }} />
                <Bar dataKey="value" name="Robustness" radius={[3, 3, 0, 0]}>
                  {scenarios.map((s, i) => (
                    <Cell key={s.scenario_id} fill={COLORS[i % COLORS.length]} opacity={s.rank === 1 ? 1 : 0.55} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Outcome distribution per scenario */}
        <Card>
          <CardHeader>
            <CardTitle>Outcome Distribution Summary</CardTitle>
            <span className="text-xs text-zinc-600">P10 / Mean / P90 access improvement per scenario</span>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800">
                  {["Scenario", "P10 (pessimistic)", "P25", "Median", "Mean", "P75", "P90 (optimistic)", "Std Dev"].map(h => (
                    <th key={h} className="pb-2 text-left text-zinc-500 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s) => {
                  const d = s.access_improvement;
                  return (
                    <tr key={s.scenario_id} className="border-b border-zinc-800/40">
                      <td className="py-2 pr-4 font-medium text-zinc-300">{interventionLabel(s.scenario_name)}</td>
                      <td className={`py-2 pr-4 ${d.p10 < 0 ? "text-red-400" : "text-zinc-400"}`}>{formatPct(d.p10)}</td>
                      <td className="py-2 pr-4 text-zinc-400">{formatPct(d.p25)}</td>
                      <td className="py-2 pr-4 text-zinc-300">{formatPct(d.median)}</td>
                      <td className="py-2 pr-4 font-semibold text-zinc-200">{formatPct(d.mean)}</td>
                      <td className="py-2 pr-4 text-zinc-400">{formatPct(d.p75)}</td>
                      <td className="py-2 pr-4 text-emerald-400">{formatPct(d.p90)}</td>
                      <td className="py-2 text-zinc-500">±{formatPct(d.std)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="flex justify-end gap-3">
          <Link href={`/app/model/${runId}`}><Button variant="secondary">View Model</Button></Link>
          <Link href={`/app/results/${runId}`}><Button>View Recommendation →</Button></Link>
        </div>
      </main>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="min-h-screen bg-zinc-950 animate-pulse">
      <div className="h-14 border-b border-zinc-800 bg-zinc-900" />
      <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
        <div className="h-8 w-1/3 rounded bg-zinc-800" />
        <div className="h-64 rounded bg-zinc-900 border border-zinc-800" />
        <div className="h-64 rounded bg-zinc-900 border border-zinc-800" />
      </div>
    </div>
  );
}
