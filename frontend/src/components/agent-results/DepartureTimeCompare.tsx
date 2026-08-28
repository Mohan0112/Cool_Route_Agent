import { Badge } from "@/components/ui/Badge"
import type { DepartureTimeOption } from "@/lib/types"

function formatHour(time: string): string {
  const [hStr] = time.split(":")
  const h = parseInt(hStr, 10)
  const period = h >= 12 ? "PM" : "AM"
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12} ${period}`
}

export function DepartureTimeCompare({ options }: { options: DepartureTimeOption[] }) {
  if (options.length === 0) return null
  const coolestTemp = Math.min(...options.map((o) => o.mean_temp_c))

  return (
    <div>
      <p className="mb-2 text-xs font-semibold tracking-wide text-[var(--text-muted)] uppercase">Best time to leave</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const isCoolest = option.mean_temp_c === coolestTemp
          return (
            <div
              key={option.time}
              className={`rounded-lg border px-3 py-2 text-center ${
                isCoolest ? "border-[var(--accent-border)] bg-[var(--accent-bg)]" : "border-[var(--border)] bg-[var(--surface-2)]"
              }`}
            >
              <p className="text-xs font-medium text-[var(--text-muted)]">{formatHour(option.time)}</p>
              <p className={`text-sm font-semibold ${isCoolest ? "text-[var(--accent)]" : "text-[var(--text)]"}`}>
                {option.mean_temp_c.toFixed(1)}&deg;C
              </p>
              {option.mean_solar_irradiance_wm2 != null && (
                <p className="text-[10px] text-[var(--text-muted)]">{option.mean_solar_irradiance_wm2.toFixed(0)} W/m&sup2;</p>
              )}
              {isCoolest && (
                <div className="mt-1">
                  <Badge tone="accent">Coolest</Badge>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
