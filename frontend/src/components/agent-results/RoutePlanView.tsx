import { Badge } from "@/components/ui/Badge"
import { Markdown } from "@/components/ui/Markdown"
import { MeasuredOutcomeStat } from "@/components/agent-results/MeasuredOutcomeStat"
import { DepartureTimeCompare } from "@/components/agent-results/DepartureTimeCompare"
import { routeColor } from "@/components/map/RouteMap"
import type { CoolRoutePlan } from "@/lib/types"

// Loosely modeled on the NWS heat index bands the backend uses (heat_risk_category in
// coolroute_agent.py) -- Badge only has 5 tones for more categories, so Caution/Extreme
// Caution share "warning" and Danger/Extreme Danger share "danger"; the label text disambiguates.
function riskTone(category?: string): "neutral" | "success" | "warning" | "danger" {
  switch (category) {
    case "Comfortable":
      return "success"
    case "Caution":
    case "Extreme Caution":
      return "warning"
    case "Danger":
    case "Extreme Danger":
      return "danger"
    default:
      return "neutral"
  }
}

export function RoutePlanView({ plan }: { plan: CoolRoutePlan }) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-[var(--text-muted)]">
          {plan.origin_label} &rarr; {plan.destination_label}
          <span className="ml-2 capitalize">({plan.mode})</span>
        </p>
        <Markdown>{plan.summary}</Markdown>
      </div>

      <MeasuredOutcomeStat outcome={plan.measured_outcome} />

      <div className="space-y-3">
        {plan.options.map((option, i) => (
          <div key={option.route_id} className="rounded-xl border border-[var(--border)] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: routeColor(option.label, i) }} />
              <span className="font-semibold text-[var(--text)]">{option.label}</span>
              <Badge tone="neutral">{option.distance_km.toFixed(1)} km</Badge>
              <Badge tone="neutral">{option.duration_min.toFixed(0)} min</Badge>
              <Badge tone="accent">mean {option.mean_temp_c.toFixed(1)}&deg;C</Badge>
              <Badge tone="neutral">max {option.max_temp_c.toFixed(1)}&deg;C</Badge>
              {option.mean_solar_irradiance_wm2 != null && (
                <Badge tone="neutral">&#9728; {option.mean_solar_irradiance_wm2.toFixed(0)} W/m&sup2;</Badge>
              )}
              {option.risk_category && <Badge tone={riskTone(option.risk_category)}>{option.risk_category}</Badge>}
            </div>
            <div className="mt-2">
              <Markdown>{option.rationale}</Markdown>
            </div>
            {option.safety_tip && option.risk_category && option.risk_category !== "Comfortable" && (
              <p className="mt-2 text-xs text-[var(--text-muted)]">
                <span className="font-medium">Safety tip:</span> {option.safety_tip}
              </p>
            )}
          </div>
        ))}
      </div>

      {plan.departure_time_comparison && plan.departure_time_comparison.length > 0 && (
        <DepartureTimeCompare options={plan.departure_time_comparison} />
      )}

      <div className="flex flex-wrap items-center gap-1 text-xs text-[var(--text-muted)]">
        <span className="font-medium">Sources:</span>
        {plan.sources.map((s) => (
          <Badge key={s} tone="neutral">
            {s}
          </Badge>
        ))}
      </div>

      {plan.caveats && (
        <p className="text-xs text-[var(--text-muted)]">
          <span className="font-medium">Caveats:</span> {plan.caveats}
        </p>
      )}
    </div>
  )
}
