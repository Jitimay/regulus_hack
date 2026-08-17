/**
 * API client — typed wrappers around all backend endpoints.
 */

import type {
  AgentEvent,
  CreateRunRequest,
  CreateRunResponse,
  PGMModel,
  Run,
  RunResult,
  ScenarioSet,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_V1}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export async function createRun(req: CreateRunRequest): Promise<CreateRunResponse> {
  return apiFetch<CreateRunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getRun(runId: string): Promise<Run> {
  return apiFetch<Run>(`/runs/${runId}`);
}

export async function getRunEvents(runId: string): Promise<AgentEvent[]> {
  return apiFetch<AgentEvent[]>(`/runs/${runId}/events`);
}

export async function getRunModel(runId: string): Promise<PGMModel> {
  return apiFetch<PGMModel>(`/runs/${runId}/model`);
}

export async function getRunScenarios(runId: string): Promise<ScenarioSet> {
  return apiFetch<ScenarioSet>(`/runs/${runId}/scenarios`);
}

export async function getRunResults(runId: string): Promise<RunResult> {
  return apiFetch<RunResult>(`/runs/${runId}/results`);
}

export async function cancelRun(runId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/runs/${runId}/cancel`, { method: "POST" });
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/health");
}
