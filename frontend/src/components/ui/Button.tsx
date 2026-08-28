import type { ButtonHTMLAttributes } from "react"
import { clsx } from "clsx"

type Variant = "primary" | "secondary" | "ghost"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] disabled:opacity-50",
  secondary:
    "bg-[var(--surface-2)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface)] disabled:opacity-50",
  ghost: "text-[var(--text-muted)] hover:text-[var(--text)] disabled:opacity-50",
}

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
}
