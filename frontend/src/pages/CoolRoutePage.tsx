import { useState } from "react"
import { clsx } from "clsx"
import { PageShell } from "@/components/layout/PageShell"
import { Card, CardHeader, CardBody } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"

import { RouteMap } from "@/components/map/RouteMap"
import { RoutePlanView } from "@/components/agent-results/RoutePlanView"
import { Markdown } from "@/components/ui/Markdown"
import { HowItWorks } from "@/components/layout/HowItWorks"
import { useAgentStream } from "@/hooks/useAgentStream"
import type { CoolRoutePlan, TravelMode } from "@/lib/types"

// The agent only reaches submit_route_plan when it can actually complete the task (both
// ends geocode, at least one route exists). When it can't -- e.g. an address it can't
// resolve -- AgentRunner ends the run with plain text and no structured payload instead.
// Trusting the CoolRoutePlan cast blindly in that case crashes the whole page (options is
// undefined), so this checks the shape actually came back before treating it as a plan.
function isCoolRoutePlan(result: Record<string, unknown> | null): result is Record<string, unknown> & CoolRoutePlan {
  return !!result && Array.isArray((result as { options?: unknown }).options)
}

const MODES: { value: TravelMode; label: string; icon: string }[] = [
  { value: "walking", label: "Walking", icon: "🚶" },
  { value: "cycling", label: "Cycling", icon: "🚲" },
  { value: "driving", label: "Driving", icon: "🚗" },
]

const EXAMPLES: { origin: string; destination: string; mode: TravelMode }[] = [
  { origin: "Phoenix Convention Center, Phoenix, AZ", destination: "Chase Field, Phoenix, AZ", mode: "walking" },
  { origin: "Tempe Town Lake, Tempe, AZ", destination: "Arizona State University, Tempe, AZ", mode: "cycling" },
  { origin: "Phoenix Sky Harbor Airport, AZ", destination: "Downtown Phoenix, AZ", mode: "driving" },
]

export function CoolRoutePage() {
  const [origin, setOrigin] = useState(EXAMPLES[0].origin)
  const [destination, setDestination] = useState(EXAMPLES[0].destination)
  const [mode, setMode] = useState<TravelMode>(EXAMPLES[0].mode)
  const [useCustomTime, setUseCustomTime] = useState(false)
  const [customTime, setCustomTime] = useState("")
  const [compareTimes, setCompareTimes] = useState(false)
  const stream = useAgentStream()
  const plan = isCoolRoutePlan(stream.result) ? (stream.result as unknown as CoolRoutePlan) : null
  const fallbackText = !plan && stream.result ? (stream.result.text as string | undefined) : undefined

  const canRun = origin.trim() !== "" && destination.trim() !== "" && stream.status !== "streaming"

  const runAgent = () => {
    const when = useCustomTime && customTime ? customTime.replace("T", " ") : "now"
    stream.run("/api/agents/coolroute/run", { origin, destination, mode, when, compare_departure_times: compareTimes })
  }

  return (
    <PageShell
      title="Sundodger"
      description="Like Google Maps, but it plans around heat: give it a start, an end, and a mode -- it geocodes both, pulls real street routes, measures real FortyGuard temperature data along each one, and recommends the coolest option."
    >
      <HowItWorks />

      <Card className="mb-6">
        <CardBody className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-[var(--text-muted)]">From</span>
              <input
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="Starting address, landmark, or city"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-[var(--text-muted)]">To</span>
              <input
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="Destination address, landmark, or city"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex overflow-hidden rounded-lg border border-[var(--border)]">
              {MODES.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value)}
                  className={clsx(
                    "px-3 py-1.5 text-sm font-medium transition-colors",
                    mode === m.value ? "bg-[var(--accent)] text-white" : "bg-[var(--surface-2)] text-[var(--text-muted)] hover:text-[var(--text)]"
                  )}
                >
                  {m.icon} {m.label}
                </button>
              ))}
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setUseCustomTime(false)}
                  className={clsx(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    !useCustomTime ? "bg-[var(--accent-bg)] text-[var(--accent)]" : "text-[var(--text-muted)] hover:text-[var(--text)]"
                  )}
                >
                  Now
                </button>
                <button
                  onClick={() => setUseCustomTime(true)}
                  className={clsx(
                    "rounded-full px-3 py-1 text-xs font-medium",
                    useCustomTime ? "bg-[var(--accent-bg)] text-[var(--accent)]" : "text-[var(--text-muted)] hover:text-[var(--text)]"
                  )}
                >
                  Choose time
                </button>
                {useCustomTime && (
                  <input
                    type="datetime-local"
                    value={customTime}
                    onChange={(e) => setCustomTime(e.target.value)}
                    className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
                  />
                )}
              </div>
              {useCustomTime && (
                <span className="text-[10px] text-[var(--text-muted)] ml-2">
                  * Forecasts only available up to 12 hours ahead.
                </span>
              )}
            </div>

            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-[var(--text-muted)]">
              <input
                type="checkbox"
                checked={compareTimes}
                onChange={(e) => setCompareTimes(e.target.checked)}
                className="accent-[var(--accent)]"
              />
              Also compare departure times
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.origin}
                onClick={() => {
                  setOrigin(ex.origin)
                  setDestination(ex.destination)
                  setMode(ex.mode)
                }}
                className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
              >
                {MODES.find((m) => m.value === ex.mode)?.icon} {ex.origin.split(",")[0]} &rarr; {ex.destination.split(",")[0]}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <Button disabled={!canRun} onClick={runAgent}>
              Find coolest route
            </Button>
            {stream.status === "streaming" && (
              <Button variant="secondary" onClick={stream.cancel}>
                Cancel
              </Button>
            )}
          </div>
          {stream.errorMessage && <p className="text-sm text-[var(--danger)]">{stream.errorMessage}</p>}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Grid items stretch, so this card grows to match the (usually taller) route-plan
            column. The map therefore fills it rather than sitting at a fixed 480px and
            leaving dead white space underneath. min-h keeps it from collapsing when the
            plan column is short, and overflow-hidden clips the map to the rounded corners. */}
        <Card className="flex flex-col overflow-hidden lg:col-span-3">
          <CardBody className="flex-1 p-0">
            <div className="h-[480px] min-h-[480px] lg:h-full">
              {plan && plan.options.length > 0 ? (
                <RouteMap
                  key={stream.runId}
                  options={plan.options}
                  originLabel={plan.origin_label}
                  destinationLabel={plan.destination_label}
                  height="100%"
                />
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-center text-sm text-[var(--text-muted)]">
                  Enter a trip above and run the agent to see routes here.
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <h2 className="text-sm font-semibold">Route plan</h2>
          </CardHeader>
          <CardBody>
            {plan ? (
              <RoutePlanView plan={plan} />
            ) : fallbackText ? (
              <Markdown>{fallbackText}</Markdown>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">Run the agent to see its ranked routes here.</p>
            )}
          </CardBody>
        </Card>
      </div>

    </PageShell>
  )
}
