import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RunStatus, AgentName } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPct(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatUSD(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function runStatusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    created: "Created",
    queued: "Queued",
    planning: "Analyzing problem",
    researching: "Gathering evidence",
    modeling: "Building model",
    simulating: "Running simulation",
    analyzing: "Sensitivity analysis",
    researching_again: "Additional research",
    finalizing: "Generating recommendation",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
  };
  return labels[status] ?? status;
}

export function agentLabel(agent: AgentName): string {
  const labels: Record<AgentName, string> = {
    orchestrator: "Orchestrator",
    research_agent: "Research Agent",
    simulation_agent: "Simulation Agent",
    decision_agent: "Decision Agent",
    system: "System",
  };
  return labels[agent] ?? agent;
}

export function isTerminal(status: RunStatus): boolean {
  return ["completed", "failed", "cancelled"].includes(status);
}

export function isRunning(status: RunStatus): boolean {
  return !isTerminal(status) && status !== "created";
}

export function interventionLabel(type: string): string {
  const labels: Record<string, string> = {
    pump_expansion: "Pump Expansion",
    storage_expansion: "Storage Expansion",
    solar_pumping: "Solar Pumping",
    distribution_improvements: "Distribution Improvements",
    combined_strategy: "Combined Strategy",
    custom: "Custom",
  };
  return labels[type] ?? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.75) return "High";
  if (confidence >= 0.5) return "Medium";
  if (confidence >= 0.25) return "Low";
  return "Very Low";
}

export function getAgentColor(agent: AgentName): string {
  const colors: Record<AgentName, string> = {
    orchestrator: "#6366f1",
    research_agent: "#06b6d4",
    simulation_agent: "#8b5cf6",
    decision_agent: "#10b981",
    system: "#6b7280",
  };
  return colors[agent] ?? "#6b7280";
}

export function getStatusColor(status: "info" | "success" | "warning" | "error"): string {
  const colors = {
    info: "#6b7280",
    success: "#10b981",
    warning: "#f59e0b",
    error: "#ef4444",
  };
  return colors[status];
}
