import type { ReactNode } from "react"
import { clsx } from "clsx"

type Tone = "neutral" | "accent" | "success" | "warning" | "danger"

const toneClasses: Record<Tone, string> = {
  neutral: "bg-[var(--surface-2)] text-[var(--text-muted)] border-[var(--border)]",
  accent: "bg-[var(--accent-bg)] text-[var(--accent)] border-[var(--accent-border)]",
  success: "bg-[var(--success-bg)] text-[var(--success)] border-transparent",
  warning: "bg-[var(--warning-bg)] text-[var(--warning)] border-transparent",
  danger: "bg-[var(--danger-bg)] text-[var(--danger)] border-transparent",
}

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        toneClasses[tone]
      )}
    >
      {children}
    </span>
  )
}
