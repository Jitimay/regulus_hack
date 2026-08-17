import Link from "next/link";
import { Navbar } from "@/components/layout/navbar";

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-12 prose prose-invert prose-zinc">
        <h1 className="text-2xl font-bold text-zinc-100 mb-2">Documentation</h1>
        <p className="text-zinc-500 mb-8">How Regulus works.</p>

        <Section title="What Regulus does">
          <p className="text-zinc-400 text-sm leading-relaxed">
            Regulus decomposes a hard infrastructure decision into a probabilistic model,
            simulates possible outcomes for each intervention, performs sensitivity analysis,
            and — when dominant uncertainty is detected — autonomously investigates further
            before producing a recommendation.
          </p>
          <p className="text-zinc-400 text-sm leading-relaxed mt-3">
            The result is not a black-box answer. Every step is logged, every assumption
            is explicit, and every number carries an uncertainty bound.
          </p>
        </Section>

        <Section title="The four agents">
          <AgentDoc
            name="Orchestrator"
            color="indigo"
            desc="Controls the workflow. Decomposes the problem, delegates research, inspects results, and decides whether more investigation is needed."
          />
          <AgentDoc
            name="Research/Data Agent"
            color="cyan"
            desc="Collects and structures evidence. Classifies each finding as external evidence, assumption, or inferred. Attaches confidence and provenance to every claim."
          />
          <AgentDoc
            name="Simulation Agent"
            color="violet"
            desc="Builds the probabilistic graphical model from evidence, configures intervention scenarios, and coordinates Monte Carlo simulation."
          />
          <AgentDoc
            name="Decision Agent"
            color="emerald"
            desc="Evaluates scenario results through multi-criteria decision analysis. Provides reasoning, risks, assumptions, and conditions for change."
          />
        </Section>

        <Section title="The autonomous loop">
          <p className="text-zinc-400 text-sm leading-relaxed">
            After the initial simulation, sensitivity analysis identifies the variable with
            the highest influence on the outcome. If the sensitivity score exceeds the
            materiality threshold (0.35), the Orchestrator triggers an additional research
            cycle targeting that variable. The PGM is updated, simulation reruns, and
            sensitivity is re-evaluated. This continues up to 3 loops.
          </p>
        </Section>

        <Section title="The probabilistic model">
          <p className="text-zinc-400 text-sm leading-relaxed">
            Regulus builds a 8-node Bayesian network representing the water infrastructure
            system. Nodes include: rainfall, electricity reliability, household demand,
            water availability, storage level, pump availability, distribution capacity,
            and water access (the target outcome).
          </p>
          <p className="text-zinc-400 text-sm leading-relaxed mt-3">
            Simulation uses Monte Carlo sampling through the DAG. Sensitivity is computed
            via one-at-a-time perturbation with Spearman rank correlation.
          </p>
        </Section>

        <Section title="Important limitations">
          <ul className="space-y-2 text-sm text-zinc-400">
            <li>• Results are scenario estimates, not predictions of the future.</li>
            <li>• The demo uses synthetic/illustrative data for a fictional region (Maji Valley).</li>
            <li>• Model parameters are approximate — real decisions require real data collection.</li>
            <li>• Consult domain experts and local stakeholders before acting on any analysis.</li>
          </ul>
        </Section>

        <div className="mt-8 pt-4 border-t border-zinc-800">
          <Link href="/app/new" className="text-indigo-400 hover:text-indigo-300 text-sm">
            Start a scenario →
          </Link>
        </div>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-zinc-100 mb-4 pb-2 border-b border-zinc-800">{title}</h2>
      {children}
    </div>
  );
}

function AgentDoc({
  name,
  color,
  desc,
}: {
  name: string;
  color: "indigo" | "cyan" | "violet" | "emerald";
  desc: string;
}) {
  const dotColors = {
    indigo: "bg-indigo-500",
    cyan: "bg-cyan-500",
    violet: "bg-violet-500",
    emerald: "bg-emerald-500",
  };
  return (
    <div className="flex gap-3 mb-4">
      <div className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${dotColors[color]}`} />
      <div>
        <div className="text-sm font-medium text-zinc-200 mb-1">{name}</div>
        <p className="text-sm text-zinc-500">{desc}</p>
      </div>
    </div>
  );
}
