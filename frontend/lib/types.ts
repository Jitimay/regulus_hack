/**
 * Frontend type definitions mirroring backend domain models.
 * Single source of truth for all API response shapes.
 */

export type RunStatus =
  | "created"
  | "queued"
  | "planning"
  | "researching"
  | "modeling"
  | "simulating"
  | "analyzing"
  | "researching_again"
  | "finalizing"
  | "completed"
  | "failed"
  | "cancelled";

export type AgentName =
  | "orchestrator"
  | "research_agent"
  | "simulation_agent"
  | "decision_agent"
  | "system";

export type EventType = string;

export type InterventionType =
  | "pump_expansion"
  | "storage_expansion"
  | "solar_pumping"
  | "distribution_improvements"
  | "combined_strategy"
  | "custom";

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

export interface Community {
  name: string;
  population?: number;
  current_access_pct?: number;
  notes?: string;
}

export interface RunInput {
  decision_question: string;
  context?: string;
  budget_usd: number;
  communities: Community[];
  objective: string;
  interventions: InterventionType[];
  demo_mode: boolean;
}

export interface Run {
  id: string;
  status: RunStatus;
  input: RunInput;
  research_loop_count: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  model_id?: string;
  result_id?: string;
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export interface AgentEvent {
  id: string;
  run_id: string;
  timestamp: string;
  agent: AgentName;
  type: EventType;
  message: string;
  status: "info" | "success" | "warning" | "error";
  duration_ms?: number;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// PGM model
// ---------------------------------------------------------------------------

export interface NodeDistribution {
  type: string;
  mean?: number;
  std?: number;
  alpha?: number;
  beta?: number;
  low?: number;
  high?: number;
  probability?: number;
}

export interface PGMNode {
  name: string;
  display_name: string;
  description: string;
  node_type: string;
  unit: string;
  distribution: NodeDistribution;
  confidence: number;
  evidence_source: string;
  evidence_status: string;
  sensitivity_score?: number;
  intervention_overrides: Record<string, Record<string, number>>;
}

export interface PGMEdge {
  parent: string;
  child: string;
  relationship: string;
  strength: number;
  direction: "positive" | "negative";
}

export interface PGMModel {
  run_id: string;
  name: string;
  nodes: PGMNode[];
  edges: PGMEdge[];
  node_count: number;
  edge_count: number;
  research_loop?: number;
}

// ---------------------------------------------------------------------------
// Scenarios
// ---------------------------------------------------------------------------

export interface Scenario {
  id: string;
  run_id: string;
  name: string;
  description: string;
  intervention_type: InterventionType;
  cost_usd: number;
  status: string;
}

export interface ScenarioSet {
  run_id: string;
  scenarios: Scenario[];
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

export interface OutcomeDistribution {
  mean: number;
  median: number;
  std: number;
  p10: number;
  p25: number;
  p75: number;
  p90: number;
  min: number;
  max: number;
  prob_target: number;
}

export interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  intervention_type: string;
  cost_usd: number;
  access_improvement: OutcomeDistribution;
  reliability_score: OutcomeDistribution;
  robustness: number;
  expected_households_served: number;
  rank: number;
  samples: number[];
}

export interface SensitivityEntry {
  variable_name: string;
  node_description: string;
  sensitivity_score: number;
  direction: "positive" | "negative";
  uncertainty_contribution: number;
}

export interface SensitivityResult {
  id: string;
  run_id: string;
  entries: SensitivityEntry[];
  dominant_variable?: string;
  dominant_uncertainty_score: number;
  is_material: boolean;
}

export interface AlternativeComparison {
  scenario_name: string;
  reason: string;
  key_weakness: string;
  expected_impact: number;
}

export interface Recommendation {
  id: string;
  run_id: string;
  recommended_scenario_id: string;
  recommended_scenario_name: string;
  intervention_type: string;
  expected_impact: number;
  expected_households_served: number;
  robustness: number;
  confidence: number;
  cost_usd: number;
  summary: string;
  reasoning: string;
  key_risks: string[];
  key_assumptions: string[];
  sensitive_variables: string[];
  alternative_comparisons: AlternativeComparison[];
  conditions_for_change: string[];
  uncertainty_notes: string;
  research_loops_completed: number;
  created_at: string;
}

export interface RunResult {
  id: string;
  run_id: string;
  scenario_results: ScenarioResult[];
  sensitivity?: SensitivityResult;
  recommendation?: Recommendation;
  baseline_access_pct: number;
  research_loop_count: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// API request/response
// ---------------------------------------------------------------------------

export interface CreateRunRequest {
  decision_question: string;
  context?: string;
  budget_usd: number;
  communities: Community[];
  objective: string;
  interventions: InterventionType[];
  custom_interventions?: string[];
  demo_mode?: boolean;
}

export interface CreateRunResponse {
  run_id: string;
  status: string;
  created_at: string;
}
