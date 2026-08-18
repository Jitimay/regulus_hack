import Link from "next/link";
import { Button } from "@/components/ui/button";

const WORKFLOW_STEPS = [
  { label: "Problem", icon: "◎", color: "text-zinc-400" },
  { label: "Research", icon: "◎", color: "text-cyan-400" },
  { label: "Model", icon: "◎", color: "text-violet-400" },
  { label: "Simulate", icon: "◎", color: "text-indigo-400" },
  { label: "Decision", icon: "◎", color: "text-emerald-400" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Navigation */}
      <header className="border-b border-zinc-800">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-indigo-600">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <span className="font-semibold tracking-tight">Regulus</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/docs" className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors">Docs</Link>
            <Link href="/app/new">
              <Button size="sm">Start a scenario</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-6 pt-24 pb-16">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-800 bg-indigo-950/50 px-4 py-1.5">
          <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-xs text-indigo-300">Autonomous Gemini Agent Workflow</span>
        </div>

        <h1 className="mb-6 text-5xl font-bold leading-tight tracking-tight text-zinc-50 lg:text-6xl">
          Explore difficult decisions<br />
          <span className="text-indigo-400">before they become</span><br />
          expensive mistakes.
        </h1>

        <p className="mb-4 max-w-2xl text-lg text-zinc-400 leading-relaxed">
          Regulus uses autonomous Gemini agents and probabilistic simulation to explore
          infrastructure decisions under uncertainty — and tells you <em>why</em>, not just <em>what</em>.
        </p>

        <p className="mb-10 max-w-2xl text-base text-zinc-500">
          Give Regulus a hard allocation problem. It researches evidence, builds a probabilistic model,
          runs Monte Carlo simulation, detects dominant uncertainties, and autonomously loops back
          for more research before finalizing a recommendation you can fully inspect.
        </p>

        <div className="flex flex-wrap items-center gap-4">
          <Link href="/app/new">
            <Button size="lg">
              Start a scenario
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Button>
          </Link>
          <Link href="/app/new?demo=true">
            <Button variant="secondary" size="lg">Run demo scenario</Button>
          </Link>
        </div>
      </section>

      {/* Workflow visualization */}
      <section className="border-t border-zinc-800 bg-zinc-900/50 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <p className="mb-10 text-center text-xs font-semibold uppercase tracking-widest text-zinc-500">
            How it works
          </p>
          <div className="flex items-center justify-center gap-0 flex-wrap">
            {WORKFLOW_STEPS.map((step, i) => (
              <div key={step.label} className="flex items-center">
                <div className="flex flex-col items-center gap-2">
                  <div className={`text-xl ${step.color}`}>{step.icon}</div>
                  <span className="text-xs font-medium text-zinc-400">{step.label}</span>
                </div>
                {i < WORKFLOW_STEPS.length - 1 && (
                  <div className="mx-3 mb-5 h-px w-12 bg-gradient-to-r from-zinc-600 to-zinc-700" />
                )}
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-sm text-zinc-500 max-w-lg mx-auto">
            After the initial simulation, Regulus identifies dominant uncertainties and autonomously
            conducts additional research — updating the model before finalizing its recommendation.
          </p>
        </div>
      </section>

      {/* Feature highlights */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="grid gap-6 md:grid-cols-3">
          <FeatureCard
            title="Probabilistic modeling"
            description="Bayesian network with Monte Carlo simulation. Every outcome comes with uncertainty bounds, not a single point estimate."
            color="indigo"
          />
          <FeatureCard
            title="Autonomous research loops"
            description="When sensitivity analysis finds a dominant uncertainty, the orchestrator initiates another evidence-gathering cycle automatically."
            color="violet"
          />
          <FeatureCard
            title="Observable execution"
            description="Watch the agent workflow in real time — every decision, evidence item, and model update is logged and visible."
            color="cyan"
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-8">
        <div className="mx-auto max-w-7xl px-6">
          <p className="text-xs text-zinc-600">
            Regulus — Built for the All Things Agentic Hackathon · Powered by Google Gemini &amp; Cloud Run ·
            Results are scenario estimates, not predictions.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  title,
  description,
  color,
}: {
  title: string;
  description: string;
  color: "indigo" | "violet" | "cyan";
}) {
  const borderColors = {
    indigo: "border-indigo-900 hover:border-indigo-700",
    violet: "border-violet-900 hover:border-violet-700",
    cyan: "border-cyan-900 hover:border-cyan-700",
  };
  const dotColors = {
    indigo: "bg-indigo-500",
    violet: "bg-violet-500",
    cyan: "bg-cyan-500",
  };
  return (
    <div className={`rounded-lg border bg-zinc-900 p-6 transition-colors ${borderColors[color]}`}>
      <div className={`mb-4 h-2 w-2 rounded-full ${dotColors[color]}`} />
      <h3 className="mb-2 font-semibold text-zinc-100">{title}</h3>
      <p className="text-sm leading-relaxed text-zinc-500">{description}</p>
    </div>
  );
}
