import Link from "next/link";
import { Button } from "@/components/ui/button";

const WORKFLOW_STEPS = [
  { label: "1. Problem Definition", desc: "Decompose question & constraints", icon: "⚡", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" },
  { label: "2. Evidence Gathering", desc: "Multi-source confidence classification", icon: "🔍", color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10" },
  { label: "3. Probabilistic PGM", desc: "Bayesian Graph & distribution fitting", icon: "🧬", color: "text-violet-400 border-violet-500/30 bg-violet-500/10" },
  { label: "4. Monte Carlo Sim", desc: "Sensitivity analysis & dominant uncertainty", icon: "🎲", color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10" },
  { label: "5. Decision & Loops", desc: "Autonomous re-research or recommendation", icon: "🎯", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {/* Background Gradient Effect */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]" />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 via-indigo-600 to-violet-600 shadow-md shadow-indigo-500/20">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="font-bold tracking-tight text-lg leading-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                Regulus
              </span>
              <span className="text-[10px] text-zinc-400 font-medium tracking-wide uppercase">
                Autonomous Infrastructure Lab
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-4">
            <Link href="/docs" className="text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors">
              Docs
            </Link>
            <Link href="/app/new">
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-sm shadow-indigo-600/30">
                Start a scenario
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 mx-auto max-w-7xl px-6 pt-10 pb-16">
        <div className="grid gap-10 lg:grid-cols-12 lg:items-center">

          {/* Hero Left Column */}
          <div className="lg:col-span-7">
            <div className="mb-4 inline-flex items-center gap-2.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-1 backdrop-blur-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </span>
              <span className="text-xs font-semibold text-indigo-300 tracking-wide uppercase">
                Powered by Google Gemini 2.5 & Cloud Run
              </span>
            </div>

            <h1 className="mb-5 text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl leading-tight">
              Explore difficult decisions <br />
              <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                before they become expensive mistakes.
              </span>
            </h1>

            <p className="mb-4 text-base text-zinc-300 leading-relaxed font-normal">
              Built by a Burundian developer who has lived infrastructure challenges firsthand.
              In peri-urban East Africa, a local authority with a $50,000 water budget must choose between
              <strong className="text-zinc-100 font-semibold"> solar pumping</strong>, <strong className="text-zinc-100 font-semibold">pump expansion</strong>, or <strong className="text-zinc-100 font-semibold">storage tanks</strong> under an unreliable grid and seasonal rainfall.
            </p>

            <p className="mb-6 text-sm text-zinc-400 leading-relaxed">
              Regulus makes that investigation rigorous. It gathers evidence, builds a Bayesian network, runs Monte Carlo simulations, detects dominant uncertainties, and <strong className="text-indigo-300">autonomously loops back for targeted re-research</strong> before finalizing recommendations.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Link href="/app/new">
                <Button size="lg" className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-5 shadow-lg shadow-indigo-600/25">
                  Start custom scenario
                  <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </Button>
              </Link>
              <Link href="/app/new?demo=true">
                <Button variant="secondary" size="lg" className="border border-zinc-700 bg-zinc-900/80 text-zinc-200 hover:bg-zinc-800 hover:text-white font-medium">
                  ⚡ Run Maji Valley demo
                </Button>
              </Link>
            </div>
          </div>

          {/* Hero Right Column — Live Simulation Preview Widget */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl border border-zinc-800 bg-zinc-900/90 p-6 shadow-2xl backdrop-blur-xl">
              <div className="mb-4 flex items-center justify-between border-b border-zinc-800/80 pb-3">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 w-2.5 rounded-full bg-indigo-500" />
                  <span className="text-xs font-semibold text-zinc-200">Demo: Maji Valley Water Access</span>
                </div>
                <span className="rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  Live Scenario
                </span>
              </div>

              {/* Scenario Metrics Preview */}
              <div className="space-y-3 mb-5">
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-semibold text-emerald-300">Option A: Solar Pumping + Storage</span>
                    <span className="text-xs font-bold text-emerald-400">84% Improvement</span>
                  </div>
                  <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full w-[84%] rounded-full" />
                  </div>
                  <div className="mt-2 flex justify-between text-[11px] text-zinc-400">
                    <span>Robustness: 92%</span>
                    <span>Downside Protection: P10 = 71%</span>
                  </div>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 opacity-90">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-medium text-zinc-300">Option B: Grid Pump Expansion</span>
                    <span className="text-xs font-bold text-amber-400">58% Improvement</span>
                  </div>
                  <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full w-[58%] rounded-full" />
                  </div>
                  <div className="mt-2 flex justify-between text-[11px] text-zinc-400">
                    <span>Robustness: 48% (High Grid Risk)</span>
                    <span>Downside Protection: P10 = 34%</span>
                  </div>
                </div>
              </div>

              {/* Agent Activity Badge */}
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                  <span className="text-xs font-medium text-zinc-300">Orchestrator Agent</span>
                </div>
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/50">
                  Re-research Loop Completed
                </span>
              </div>
            </div>
          </div>

        </div>

        {/* Workflow Steps Section */}
        <div className="mt-16 border-t border-zinc-800/80 pt-12">
          <p className="mb-6 text-center text-xs font-semibold uppercase tracking-widest text-zinc-400">
            Autonomous Investigation Lifecycle
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {WORKFLOW_STEPS.map((step) => (
              <div key={step.label} className="flex flex-col justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/50 p-3.5 hover:border-zinc-700 transition-colors">
                <div>
                  <div className={`mb-2 inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-xs font-medium ${step.color}`}>
                    <span>{step.icon}</span>
                    <span>{step.label}</span>
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Features Cards Section */}
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          <FeatureCard
            title="Probabilistic Graphical Modeling"
            description="Uses Bayesian networks and Monte Carlo simulations. Outcome distributions are produced with full uncertainty bounds, never single-point estimates."
            badge="PGM Math Engine"
            border="border-indigo-500/20 hover:border-indigo-500/40"
            icon="📊"
          />
          <FeatureCard
            title="Autonomous Re-Research Loops"
            description="When variance decomposition detects material uncertainty (sensitivity ≥ 0.35), the Orchestrator initiates follow-up research cycles autonomously."
            badge="Agentic AI"
            border="border-violet-500/20 hover:border-violet-500/40"
            icon="🔄"
          />
          <FeatureCard
            title="Observable & Verifiable Execution"
            description="Watch every state transition, evidence finding, model graph update, and decision risk evaluation in real time."
            badge="Full Transparency"
            border="border-cyan-500/20 hover:border-cyan-500/40"
            icon="👁️"
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/80 bg-zinc-950 py-5">
        <div className="mx-auto max-w-7xl px-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-zinc-400">
            Regulus — Built for the All Things Agentic Hackathon · Powered by Google Gemini &amp; Cloud Run
          </p>
          <p className="text-[11px] text-zinc-400">
            Results are scenario estimates, not policy guarantees.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  title,
  description,
  badge,
  border,
  icon,
}: {
  title: string;
  description: string;
  badge: string;
  border: string;
  icon: string;
}) {
  return (
    <div className={`rounded-xl border bg-zinc-900/80 p-5 transition-all duration-200 ${border}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
        <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider bg-zinc-800 px-2 py-0.5 rounded border border-zinc-700">
          {badge}
        </span>
      </div>
      <h3 className="mb-1.5 font-semibold text-zinc-100">{title}</h3>
      <p className="text-xs leading-relaxed text-zinc-400">{description}</p>
    </div>
  );
}
