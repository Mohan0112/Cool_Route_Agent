import { Badge } from "@/components/ui/Badge"
import { useUsage } from "@/hooks/useUsage"

/** Inline (not <img src="/favicon.svg">) so the mark ships in the same paint as the
 *  header text -- a separate request makes the logo pop in a frame late on first load. */
function SundodgerMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <defs>
        <linearGradient id="sundodger-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fb923c" />
          <stop offset="1" stopColor="#ea580c" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7" fill="url(#sundodger-mark)" />
      <g fill="none" stroke="#fff" strokeLinecap="round">
        <circle cx="22.5" cy="9" r="3.6" fill="#fff" stroke="none" />
        <g strokeWidth="1.6">
          <path d="M22.5 2.2v1.9" />
          <path d="M28.6 9h-1.9" />
          <path d="M27 4.5l-1.4 1.4" />
          <path d="M18 4.5l1.4 1.4" />
          <path d="M27 13.5l-1.4-1.4" />
        </g>
        <path d="M5 27c0-7 5.5-9 9.5-9s5.5 4.5 11 4.5" strokeWidth="3.2" />
      </g>
    </svg>
  )
}

export function NavBar() {
  const usage = useUsage()

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg)]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold tracking-tight whitespace-nowrap">
          <SundodgerMark className="h-5 w-5 shrink-0" />
          FortyGuard <span className="text-[var(--accent)]">Sundodger</span>
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
