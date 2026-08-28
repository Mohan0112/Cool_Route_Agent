import { Badge } from "@/components/ui/Badge"
import { useUsage } from "@/hooks/useUsage"

export function NavBar() {
  const usage = useUsage()

  return (
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <span className="text-sm font-semibold tracking-tight whitespace-nowrap">
          🌡️ FortyGuard <span className="text-[var(--accent)]">CoolRoute</span>
        </span>
        <div className="ml-auto flex items-center gap-2">
          {usage.demoMode !== null && (
            <Badge tone={usage.demoMode ? "warning" : "success"}>
              {usage.demoMode ? "Demo mode" : "Live mode"}
            </Badge>
          )}
          {/* Credit balance is only meaningful in live mode -- demo mode always returns a
              static placeholder number, so showing it there would look like real tracking. */}
          {usage.demoMode === false && usage.remainingCredits !== null && (
            <Badge tone="neutral">{usage.remainingCredits.toLocaleString()} credits left</Badge>
          )}
        </div>
      </div>
    </header>
  )
}
