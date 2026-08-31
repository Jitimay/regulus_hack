"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { createRun } from "@/lib/api";
import { CreateRunSchema, type CreateRunFormValues } from "@/lib/validation";
import { Navbar } from "@/components/layout/navbar";
import type { InterventionType } from "@/lib/types";

const DEMO_VALUES: CreateRunFormValues = {
  decision_question:
    "How should we allocate $50,000 to improve reliable water access across three communities in Bujumbura's peri-urban zone?",
  context:
    "Peri-urban communities near Bujumbura, Burundi. Three communities: Kijani, Mtoni, and Amani. The electricity grid runs approximately 10–14 hours per day, making conventional electric pumps unreliable. Pump failures are routine. Rainfall is seasonal with moderate inter-annual variability. Budget is scarce — a wrong allocation is a multi-year setback.",
  budget_usd: 50000,
  communities: [
    { name: "Kijani", population: 6000, current_access_pct: 0.42, notes: "Largest community, most affected by grid outages" },
    { name: "Mtoni", population: 4000, current_access_pct: 0.55, notes: "River proximity provides partial water availability" },
    { name: "Amani", population: 3000, current_access_pct: 0.48, notes: "Highest elevation, storage shortfalls common" },
  ],
  objective:
    "Maximize reliable household water access while controlling downside risk",
  interventions: ["pump_expansion", "storage_expansion", "solar_pumping", "combined_strategy"],
  demo_mode: true,
};

const INTERVENTIONS: { value: InterventionType; label: string; description: string }[] = [
  { value: "pump_expansion", label: "Pump Expansion", description: "Additional electric pumps and infrastructure" },
  { value: "storage_expansion", label: "Storage Expansion", description: "New tanks and reservoir capacity" },
  { value: "solar_pumping", label: "Solar Pumping", description: "Solar-powered systems, grid-independent" },
  { value: "distribution_improvements", label: "Distribution Improvements", description: "Pipe network upgrades" },
  { value: "combined_strategy", label: "Combined Strategy", description: "Balanced investment across systems" },
];

const OBJECTIVES = [
  "Maximize reliable household water access while controlling downside risk",
  "Maximize water access coverage across all communities",
  "Minimize shortage risk under worst-case conditions",
  "Balance cost efficiency and access improvement",
];

// Wrap in Suspense because useSearchParams requires it
export default function NewScenarioPage() {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar />
      <Suspense fallback={<FormSkeleton />}>
        <NewScenarioForm />
      </Suspense>
    </div>
  );
}

function NewScenarioForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isDemo = searchParams.get("demo") === "true";

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [communityCount, setCommunityCount] = useState(3);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<CreateRunFormValues, unknown, CreateRunFormValues>({
    resolver: zodResolver(CreateRunSchema) as any,
    defaultValues: isDemo
      ? DEMO_VALUES
      : {
          budget_usd: 50000,
          communities: [{ name: "" }, { name: "" }, { name: "" }],
          interventions: ["pump_expansion", "solar_pumping", "combined_strategy"],
          demo_mode: false,
        },
  });

  const selectedInterventions = watch("interventions") ?? [];

  function toggleIntervention(value: string) {
    const current = getValues("interventions") ?? [];
    if (current.includes(value)) {
      setValue("interventions", current.filter((v) => v !== value));
    } else {
      setValue("interventions", [...current, value]);
    }
  }

  async function onSubmit(data: CreateRunFormValues) {
    setIsSubmitting(true);
    setError(null);
    try {
      const communities = data.communities.slice(0, communityCount).filter((c) => c.name.trim());
      const response = await createRun({
        ...data,
        communities,
        interventions: data.interventions as InterventionType[],
      });
      router.push(`/app/runs/${response.run_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create run");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="mb-8">
        <h1 className="mb-2 text-2xl font-bold text-zinc-100">New Scenario</h1>
        <p className="text-sm text-zinc-500">
          Define your decision problem. Regulus will research, model, and simulate it autonomously.
        </p>
      </div>

      {isDemo && (
        <div className="mb-8 rounded-lg border border-amber-800 bg-amber-950/30 p-4">
          <p className="text-sm text-amber-400">
            <strong>Demo mode:</strong> Pre-filled with the Maji Valley demonstration scenario using
            synthetic/illustrative data. Submit to run the full agent workflow.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-8">
        {/* Decision Question */}
        <Field label="Decision Question" error={errors.decision_question?.message} required>
          <textarea
            {...register("decision_question")}
            rows={3}
            placeholder="How should we allocate $50,000 to improve water access across three communities?"
            className="w-full rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>

        {/* Context */}
        <Field label="Context" error={errors.context?.message}>
          <textarea
            {...register("context")}
            rows={3}
            placeholder="Relevant background, region, current state..."
            className="w-full rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>

        {/* Budget */}
        <Field label="Budget (USD)" error={errors.budget_usd?.message} required>
          <input
            {...register("budget_usd")}
            type="number"
            min={0}
            step={1000}
            className="w-48 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Field>

        {/* Communities */}
        <fieldset>
          <legend className="mb-3 text-sm font-medium text-zinc-300">
            Communities <span className="text-red-400">*</span>
          </legend>
          <div className="space-y-2">
            {Array.from({ length: communityCount }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <input
                  {...register(`communities.${i}.name`)}
                  placeholder={`Community ${i + 1} name`}
                  className="flex-1 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                <input
                  {...register(`communities.${i}.population`)}
                  type="number"
                  placeholder="Population"
                  className="w-32 rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setCommunityCount((n) => Math.min(n + 1, 8))}
            className="mt-2 text-xs text-indigo-400 hover:text-indigo-300"
          >
            + Add community
          </button>
        </fieldset>

        {/* Objective */}
        <Field label="Objective" error={errors.objective?.message} required>
          <select
            {...register("objective")}
            className="w-full rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {OBJECTIVES.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </Field>

        {/* Interventions */}
        <fieldset>
          <legend className="mb-3 text-sm font-medium text-zinc-300">
            Candidate Interventions <span className="text-red-400">*</span>
          </legend>
          {errors.interventions && (
            <p className="mb-2 text-xs text-red-400">{errors.interventions.message}</p>
          )}
          <div className="space-y-2">
            {INTERVENTIONS.map((intervention) => {
              const checked = selectedInterventions.includes(intervention.value);
              return (
                <label
                  key={intervention.value}
                  className={`flex cursor-pointer items-start gap-3 rounded border p-3 transition-colors ${
                    checked
                      ? "border-indigo-700 bg-indigo-950/40"
                      : "border-zinc-800 hover:border-zinc-700"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleIntervention(intervention.value)}
                    className="mt-0.5 h-4 w-4 rounded accent-indigo-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-zinc-200">{intervention.label}</div>
                    <div className="text-xs text-zinc-500">{intervention.description}</div>
                  </div>
                </label>
              );
            })}
          </div>
        </fieldset>

        {error && (
          <div className="rounded border border-red-800 bg-red-950/30 p-3">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        <div className="flex items-center gap-4 pt-4">
          <Button type="submit" size="lg" loading={isSubmitting} className="flex-1 sm:flex-none">
            {isSubmitting ? "Starting analysis..." : "Start analysis"}
          </Button>
          <p className="text-xs text-zinc-600">
            Creates an asynchronous run — results update in real time.
          </p>
        </div>
      </form>
    </main>
  );
}

function Field({
  label,
  error,
  required,
  children,
}: {
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-zinc-300">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

function FormSkeleton() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-zinc-800" />
      <div className="h-24 rounded bg-zinc-800" />
      <div className="h-16 rounded bg-zinc-800" />
    </main>
  );
}
