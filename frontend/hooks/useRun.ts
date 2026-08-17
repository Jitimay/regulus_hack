"use client";

import { useQuery } from "@tanstack/react-query";
import { getRun, getRunEvents, getRunModel, getRunResults } from "@/lib/api";
import { isTerminal } from "@/lib/utils";
import type { Run } from "@/lib/types";

const POLL_INTERVAL = 2000; // 2s while running

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    refetchInterval: (query) => {
      const run = query.state.data as Run | undefined;
      if (!run) return POLL_INTERVAL;
      return isTerminal(run.status) ? false : POLL_INTERVAL;
    },
    enabled: !!runId,
  });
}

export function useRunEvents(runId: string, isRunning: boolean) {
  return useQuery({
    queryKey: ["run-events", runId],
    queryFn: () => getRunEvents(runId),
    refetchInterval: isRunning ? POLL_INTERVAL : false,
    enabled: !!runId,
  });
}

export function useRunModel(runId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["run-model", runId],
    queryFn: () => getRunModel(runId),
    enabled: enabled && !!runId,
    retry: 3,
    retryDelay: 2000,
  });
}

export function useRunResults(runId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["run-results", runId],
    queryFn: () => getRunResults(runId),
    enabled: enabled && !!runId,
    retry: 3,
    retryDelay: 2000,
  });
}
