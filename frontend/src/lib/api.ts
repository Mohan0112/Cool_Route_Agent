import { API_BASE_URL } from "./config"
import type { UsageSummary } from "./types"

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`${resp.status} ${resp.statusText}: ${text.slice(0, 300)}`)
  }
  return resp.json() as Promise<T>
}

export const api = {
  getUsage: () => jsonFetch<UsageSummary>("/api/usage"),

  getCoolRouteRun: (runId: string) => jsonFetch<Record<string, unknown>>(`/api/agents/coolroute/runs/${runId}`),
}
