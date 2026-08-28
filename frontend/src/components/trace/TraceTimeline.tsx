import { clsx } from "clsx"
import type { TraceEvent } from "@/lib/types"

const ICONS: Record<TraceEvent["type"], string> = {
  run_started: "▶",
  tool_call: "→",
  tool_result: "✓",
  tool_error: "✕",
  progress: "…",
  final: "★",
  error: "!",
  run_finished: "■",
}

const TONE_CLASSES: Record<TraceEvent["type"], string> = {
  run_started: "text-[var(--text-muted)]",
  tool_call: "text-[var(--accent)]",
  tool_result: "text-[var(--success)]",
  tool_error: "text-[var(--danger)]",
  progress: "text-[var(--text-muted)]",
  final: "text-[var(--accent)]",
  error: "text-[var(--danger)]",
  run_finished: "text-[var(--text-muted)]",
}

function summarize(event: TraceEvent): string {
  const d = event.data
  switch (event.type) {
    case "run_started":
      return "Run started"
    case "tool_call":
      return `Calling ${d.name as string}`
    case "tool_result":
      return `${d.name as string} returned a result`
    case "tool_error":
      return `${d.name as string} failed: ${d.error as string}`
    case "progress":
      return `${d.tool as string}: ${d.message as string}`
    case "final":
      return "Final answer produced"
    case "error":
      return `Error: ${d.message as string}`
    case "run_finished":
      return `Run finished (${d.status as string})`
    default:
      return JSON.stringify(d)
  }
}

function DetailBlock({ event }: { event: TraceEvent }) {
  const payload = event.type === "tool_call" ? event.data.args : event.type === "tool_result" ? event.data.result : null
  if (payload == null) return null
  return (
    <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-[var(--surface-2)] p-2 text-xs text-[var(--text-muted)]">
      {JSON.stringify(payload, null, 2)}
    </pre>
  )
}

export function TraceTimeline({ events }: { events: TraceEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-[var(--text-muted)]">No activity yet — run the agent to see its reasoning here.</p>
  }

  return (
    <ol className="space-y-2">
      {events.map((event) => (
        <li key={event.seq} className="flex gap-3 text-sm">
          <span
            className={clsx(
              "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-xs",
              TONE_CLASSES[event.type]
            )}
          >
            {ICONS[event.type] ?? "•"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="break-words text-[var(--text)]">{summarize(event)}</p>
            <DetailBlock event={event} />
          </div>
        </li>
      ))}
    </ol>
  )
}
