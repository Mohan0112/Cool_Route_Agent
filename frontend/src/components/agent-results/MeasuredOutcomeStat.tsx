export function MeasuredOutcomeStat({ outcome }: { outcome: string }) {
  return (
    <div className="rounded-xl border border-[var(--accent-border)] bg-[var(--accent-bg)] px-4 py-3">
      <p className="text-xs font-semibold tracking-wide text-[var(--accent)] uppercase">Measured outcome</p>
      <p className="mt-1 text-sm font-medium text-[var(--text)]">{outcome}</p>
    </div>
  )
}
