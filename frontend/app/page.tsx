import Link from "next/link";
import { Button } from "@/components/ui/button";

const WORKFLOW_STEPS = [
  { step: "01", label: "Problem Definition", desc: "Decompose question & constraints into DAG schema", icon: "⚡", color: "text-amber-400 border-amber-500/30 bg-amber-500/10" },
  { step: "02", label: "Evidence Gathering", desc: "Gather multi-source evidence & confidence scores", icon: "🔍", color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10" },
  { step: "03", label: "Probabilistic PGM", desc: "Build Bayesian Graph & fit priors/pivots", icon: "🧬", color: "text-violet-400 border-violet-500/30 bg-violet-500/10" },
  { step: "04", label: "Monte Carlo Sim", desc: "Simulate outcomes & decompose variance", icon: "🎲", color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10" },
  { step: "05", label: "Decision & Loops", desc: "Trigger re-research loops or synthesize report", icon: "🎯", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col justify-between font-sans selection:bg-indigo-500 selection:text-white">
      {/* Background Glow */}
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.12),transparent_50%)]" />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-md shadow-indigo-500/20 shrink-0">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-bold tracking-tight text-xl text-white">
                Regulus
              </span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider bg-zinc-900 border border-zinc-800 px-2.5 py-0.5 rounded-full">
                Autonomous Infrastructure Lab
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-5">
            <Link href="/docs" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Docs
            </Link>
            <Link href="/app/new">
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm shadow-indigo-600/30 px-4">
                Start a scenario
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 mx-auto w-full max-w-6xl px-6 sm:px-8 py-10 lg:py-14 space-y-16">

        {/* Hero Section */}
        <section className="grid gap-10 lg:grid-cols-12 lg:items-center">

          {/* Left Column - Headline & Pitch */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-1 text-xs font-semibold text-indigo-300">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
              </span>
              Powered by Google Gemini 2.5 &amp; Cloud Run
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-[1.15]">
              Explore difficult decisions <br className="hidden sm:inline" />
              <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-cyan-400 bg-clip-text text-transparent">
                before they become expensive mistakes.
              </span>
            </h1>

            <p className="text-base text-zinc-300 leading-relaxed">
              Built by a Burundian developer who has lived infrastructure challenges firsthand.
              In peri-urban East Africa, a local authority with a $50,000 water budget must choose between
              {" "}<strong className="text-white font-semibold">solar pumping</strong>, <strong className="text-white font-semibold">pump expansion</strong>, or <strong className="text-white font-semibold">storage tanks</strong> under an unreliable grid and seasonal rainfall.
            </p>

            <p className="text-sm text-zinc-400 leading-relaxed">
              Regulus makes that investigation rigorous. It gathers evidence, builds a Bayesian network, runs Monte Carlo simulations, detects dominant uncertainties, and <strong className="text-indigo-300 font-medium">autonomously loops back for targeted re-research</strong> before finalizing recommendations.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <Link href="/app/new">
                <Button size="lg" className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 shadow-lg shadow-indigo-600/25 rounded-xl">
                  Start custom scenario
                  <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </Button>
              </Link>
              <Link href="/app/new?demo=true">
                <Button variant="secondary" size="lg" className="border border-zinc-700 bg-zinc-900/90 text-zinc-200 hover:bg-zinc-800 hover:text-white font-medium rounded-xl">
                  ⚡ Run Maji Valley demo
                </Button>
              </Link>
            </div>
          </div>

          {/* Right Column - Live Simulation Widget */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/90 p-5 shadow-2xl backdrop-blur-md space-y-4">

              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-semibold text-zinc-200">Demo: Maji Valley Water Access</span>
                </div>
                <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  Live Preview
                </span>
              </div>

              {/* Option Cards */}
              <div className="space-y-3">
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-emerald-300">Option A: Solar Pumping + Storage</span>
                    <span className="font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/30">
                      84% Improvement
                    </span>
                  </div>
                  <div className="w-full bg-zinc-800/80 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full w-[84%] rounded-full transition-all duration-500" />
                  </div>
                  <div className="flex justify-between text-[11px] text-zinc-400 pt-0.5">
                    <span>Robustness: <strong>92%</strong></span>
                    <span>Downside P10: <strong>71%</strong></span>
                  </div>
                </div>

                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium text-zinc-300">Option B: Grid Pump Expansion</span>
                    <span className="font-bold text-amber-400 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-500/30">
                      58% Improvement
                    </span>
                  </div>
                  <div className="w-full bg-zinc-800/80 h-2 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full w-[58%] rounded-full" />
                  </div>
                  <div className="flex justify-between text-[11px] text-zinc-400 pt-0.5">
                    <span>Robustness: <strong>48%</strong> (High Grid Risk)</span>
                    <span>Downside P10: <strong>34%</strong></span>
                  </div>
                </div>
              </div>

              {/* Agent Activity Footer */}
              <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/90 p-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  <span className="text-zinc-300 font-medium">Orchestrator Agent</span>
                </div>
                <span className="text-[11px] text-cyan-400 font-mono bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                  Re-research Loop Completed
                </span>
              </div>

            </div>
          </div>

        </section>

        {/* Workflow Lifecycle Pipeline */}
        <section className="space-y-6 pt-4">
          <div className="text-center space-y-1">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400">
              Autonomous Investigation Lifecycle
            </h2>
            <p className="text-sm text-zinc-400">
              From natural language question to probabilistic Bayesian decision synthesis
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {WORKFLOW_STEPS.map((step) => (
              <div
                key={step.step}
                className="group relative rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-900/80 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-zinc-400">{step.step}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-md border font-medium ${step.color}`}>
                      {step.icon}
                    </span>
                  </div>
                  <h3 className="text-xs font-semibold text-zinc-100 mb-1">{step.label}</h3>
                  <p className="text-[11px] text-zinc-400 leading-snug">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="grid gap-6 md:grid-cols-3">
          <FeatureCard
            title="Probabilistic Graphical Modeling"
            description="Uses Bayesian networks and Monte Carlo simulations. Outcome distributions are produced with full uncertainty bounds, never single-point estimates."
            badge="PGM Math Engine"
            icon="📊"
            accent="border-indigo-500/30 hover:border-indigo-500/60"
          />
          <FeatureCard
            title="Autonomous Re-Research Loops"
            description="When variance decomposition detects material uncertainty (sensitivity ≥ 0.35), the Orchestrator initiates follow-up research cycles autonomously."
            badge="Agentic AI"
            icon="🔄"
            accent="border-violet-500/30 hover:border-violet-500/60"
          />
          <FeatureCard
            title="Observable & Verifiable Execution"
            description="Watch every state transition, evidence finding, model graph update, and decision risk evaluation in real time with full auditability."
            badge="Full Transparency"
            icon="👁️"
            accent="border-cyan-500/30 hover:border-cyan-500/60"
          />
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/80 bg-zinc-950 py-6">
        <div className="mx-auto max-w-6xl px-6 sm:px-8 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-zinc-400">
          <p>
            Regulus — Built for the All Things Agentic Hackathon · Powered by Google Gemini &amp; Cloud Run
          </p>
          <p className="text-zinc-400">
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
  icon,
  accent,
}: {
  title: string;
  description: string;
  badge: string;
  icon: string;
  accent: string;
}) {
  return (
    <div className={`rounded-2xl border bg-zinc-900/50 p-6 transition-all duration-200 hover:bg-zinc-900/80 flex flex-col justify-between ${accent}`}>
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-2xl">{icon}</span>
          <span className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase bg-zinc-800/80 px-2.5 py-1 rounded-md border border-zinc-700/60">
            {badge}
          </span>
        </div>
        <h3 className="text-base font-semibold text-zinc-100 mb-2">{title}</h3>
        <p className="text-xs leading-relaxed text-zinc-400">{description}</p>
      </div>
    </div>
  );
}
