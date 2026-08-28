import type { ReactNode } from "react"

export function PageShell({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text)]">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-[var(--text-muted)]">{description}</p>}
      </div>
      {children}
    </main>
  )
}
