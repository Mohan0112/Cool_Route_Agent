import { useCallback, useRef, useState } from "react"
import { API_BASE_URL } from "@/lib/config"
import { parseSseStream } from "@/lib/sse"
import type { TraceEvent } from "@/lib/types"

export type StreamStatus = "idle" | "streaming" | "succeeded" | "failed"

interface UseAgentStreamResult {
  status: StreamStatus
  events: TraceEvent[]
  result: Record<string, unknown> | null
  errorMessage: string | null
  runId: string | null
  run: (url: string, body: unknown) => Promise<void>
  cancel: () => void
  reset: () => void
}

export function useAgentStream(): UseAgentStreamResult {
  const [status, setStatus] = useState<StreamStatus>("idle")
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [runId, setRunId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    setStatus("idle")
    setEvents([])
    setResult(null)
    setErrorMessage(null)
    setRunId(null)
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const run = useCallback(async (url: string, body: unknown) => {
    reset()
    setStatus("streaming")
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const resp = await fetch(`${API_BASE_URL}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!resp.ok || !resp.body) {
        throw new Error(`${resp.status} ${resp.statusText}`)
      }

      for await (const raw of parseSseStream(resp.body)) {
        let data: Record<string, unknown> = {}
        try {
          data = JSON.parse(raw.data)
        } catch {
          data = { raw: raw.data }
        }

        // seq is derived from prev.length INSIDE the updater (not an external mutable
        // counter) so it stays correct even if StrictMode replays an older updater call
        // after later events have already landed -- confirmed necessary by a real duplicate
        // React key warning caught via live browser testing.
        setEvents((prev) => [...prev, { seq: prev.length + 1, type: raw.event as TraceEvent["type"], data }])

        if (raw.event === "run_started" && typeof data.run_id === "string") {
          setRunId(data.run_id)
        } else if (raw.event === "final") {
          setResult((data.structured as Record<string, unknown>) ?? { text: data.text })
        } else if (raw.event === "error") {
          setErrorMessage(String(data.message ?? "Agent run failed."))
        } else if (raw.event === "run_finished") {
          setStatus(data.status === "succeeded" ? "succeeded" : "failed")
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setErrorMessage((err as Error).message)
        setStatus("failed")
      }
    }
  }, [reset])

  return { status, events, result, errorMessage, runId, run, cancel, reset }
}
