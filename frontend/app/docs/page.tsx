import Link from "next/link";
import { Button } from "@/components/ui/button";

const SECTIONS = [
  {
    id: "overview",
    title: "Overview",
    content: `Regulus is an autonomous infrastructure decision laboratory. It uses four coordinated Gemini agents and a probabilistic simulation engine to research, model, simulate, and recommend — without a human manually orchestrating every step.

The central idea: after the initial simulation, Regulus identifies the dominant uncertain variable via sensitivity analysis and autonomously decides whether to gather more evidence. If the uncertainty is material (score ≥ 0.35), it triggers another research → model → simulate cycle before finalizing its recommendation.`,
  },
  {
    id: "agents",
    title: "Agents",
    content: null,
    agents: [
      {
        name: "Orchestrator",
        color: "indigo",
        desc: "Controls the entire workflow. Decomposes the problem, delegates to other agents, inspects sensitivity results, and decides autonomously whether to loop. Maintains explicit OrchestratorState — not conversation history.",
      },
      {
        name: "Research / Data",
        color: "cyan",
        desc: "Collects structured evidence. Classifies every item as external_evidence, assumption, inferred, or computed. Attaches confidence and provenance. In demo mode, uses the synthetic Maji Valley dataset.",
      },
      {
        name: "Simulation",
        color: "violet",
        desc: "Translates evidence into a PGM, configures intervention scenarios, and coordinates Monte Carlo simulation. Does NOT use Gemini for math — all probability calculations happen in Python (NumPy/SciPy).",
      },
      {
        name: "Decision",
        color: "emerald",
        desc: "Produces the final recommendation. The recommended scenario is always rank #1 from the simulation engine — Gemini adds reasoning, risks, assumptions, and conditions for change, but cannot override the computed ranking.",
      },
    ],
  },
  {
    id: "pgm",
    title: "Probabilistic Model",
    content: `The PGM is an 8-node Bayesian network (DAG) representing the water infrastructure system:

  rainfall → water_availability → distribution_capacity → water_access (target)
  rainfall → storage_level → distribution_capacity
  electricity_reliability → pump_availability → distribution_capacity
  household_demand → water_access (negative edge)

Each node has a parameterized distribution (Normal or Beta). Intervention scenarios modify node parameters — for example, solar_pumping replaces electricity_reliability's Beta(3,2) with Beta(9,1), effectively removing grid dependency.`,
  },
  {
    id: "simulation",
    title: "Simulation",
    content: `Monte Carlo propagation runs N samples (500 dev / 2000 demo) through the DAG in topological order. For each node, samples are drawn from its distribution and blended with parent influence (max 50% weight, scaled by edge strength and direction).

Scenario ranking uses a composite score:
  50% — expected access improvement (mean)
  30% — robustness: P(outcome ≥ 0.60)
  20% — downside protection (P10)

Sensitivity analysis uses one-at-a-time perturbation (+10% to each node's mean) combined with Spearman rank correlation. Scores are normalized to [0,1]. A score ≥ 0.35 is considered material and triggers another research loop.`,
  },
  {
    id: "loop",
    title: "Autonomous Loop",
    content: `After the initial simulation:

  1. Orchestrator inspects sensitivity results
  2. Identifies the dominant uncertain variable
  3. If score ≥ 0.35 (material) and loops < 3:
     a. Emits UNCERTAINTY_DETECTED event
     b. Calls Research Agent with target_variable
     c. Merges new evidence with prior findings
     d. Rebuilds PGM with updated parameters
     e. Reruns simulation + sensitivity
     f. Evaluates materiality again
  4. When uncertainty is resolved or max loops reached → Decision Agent

This loop is the core agentic behavior. It is visible in real time on the Run page.`,
  },
  {
    id: "data",
    title: "Demo Data",
    content: `The demo scenario uses a fictional region (Maji Valley) with three communities: Kijani, Mtoni, and Amani. All data is synthetic and clearly labeled as illustrative.

The demo still executes the real architecture — agents run, the PGM is built, Monte Carlo simulation executes, sensitivity is computed, and the recommendation is generated from actual results. Demo mode is not a fake animation.`,
  },
  {
    id: "stack",
    title: "Technology",
    content: null,
    stack: [
      { layer: "Frontend", tech: "Next.js 15, TypeScript, Tailwind CSS, Recharts, React Flow, TanStack Query" },
      { layer: "Backend", tech: "Python 3.12+, FastAPI, Pydantic, structlog" },
      { layer: "AI", tech: "Google Gemini (gemini-2.0-flash-exp), 4 autonomous agents" },
      { layer: "Math", tech: "NumPy, SciPy, NetworkX, Monte Carlo simulation" },
      { layer: "Cloud", tech: "Google Cloud Run, Firestore, Pub/Sub" },
    ],
  },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="font-semibold text-sm text-zinc-100">Regulus</Link>
            <span className="text-zinc-700">/</span>
            <span className="text-sm text-zinc-400">Documentation</span>
          </div>
          <Link href="/app/new"><Button size="sm">Start a scenario</Button></Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-zinc-50 mb-3">Documentation</h1>
          <p className="text-zinc-500">How Regulus works — agents, probabilistic model, simulation, and the autonomous loop.</p>
        </div>

        {/* TOC */}
        <nav className="mb-12 flex flex-wrap gap-3">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="text-xs text-zinc-500 hover:text-zinc-300 border border-zinc-800 rounded px-3 py-1.5 transition-colors">
              {s.title}
            </a>
          ))}
        </nav>

        <div className="space-y-16">
          {SECTIONS.map((section) => (
            <section key={section.id} id={section.id}>
              <h2 className="text-xl font-bold text-zinc-100 mb-4 pb-2 border-b border-zinc-800">
                {section.title}
              </h2>

              {section.content && (
                <div className="text-sm text-zinc-400 leading-relaxed whitespace-pre-line">
                  {section.content}
                </div>
              )}

              {section.agents && (
                <div className="grid gap-4 sm:grid-cols-2">
                  {section.agents.map((agent) => {
                    const borderColors: Record<string, string> = {
                      indigo: "border-indigo-900",
                      cyan: "border-cyan-900",
                      violet: "border-violet-900",
                      emerald: "border-emerald-900",
                    };
                    const dotColors: Record<string, string> = {
                      indigo: "bg-indigo-500",
                      cyan: "bg-cyan-500",
                      violet: "bg-violet-500",
                      emerald: "bg-emerald-500",
                    };
                    return (
                      <div key={agent.name} className={`rounded-lg border bg-zinc-900 p-5 ${borderColors[agent.color]}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <div className={`h-2 w-2 rounded-full ${dotColors[agent.color]}`} />
                          <span className="font-semibold text-zinc-200 text-sm">{agent.name}</span>
                        </div>
                        <p className="text-xs text-zinc-500 leading-relaxed">{agent.desc}</p>
                      </div>
                    );
                  })}
                </div>
              )}

              {section.stack && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800">
                        <th className="pb-2 text-left text-xs text-zinc-500 pr-8">Layer</th>
                        <th className="pb-2 text-left text-xs text-zinc-500">Technology</th>
                      </tr>
                    </thead>
                    <tbody>
                      {section.stack.map((row) => (
                        <tr key={row.layer} className="border-b border-zinc-800/50">
                          <td className="py-2.5 pr-8 font-medium text-zinc-300 text-sm">{row.layer}</td>
                          <td className="py-2.5 text-zinc-500 text-sm">{row.tech}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-zinc-800">
          <p className="text-xs text-zinc-600">
            Regulus — Built for the All Things Agentic Hackathon · Results are scenario estimates, not predictions.
            Consult domain experts before acting on any analysis.
          </p>
        </div>
      </div>
    </div>
  );
}
