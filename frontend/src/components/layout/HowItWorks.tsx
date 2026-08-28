const STEPS = [
  { icon: "📍", title: "Geocode", description: "Resolves your start and end into real coordinates" },
  { icon: "🛣️", title: "Real routes", description: "Pulls real street-level route alternatives from OSRM" },
  { icon: "🌡️", title: "Real heat data", description: "Measures actual temperature + sun exposure via FortyGuard" },
]

export function HowItWorks() {
  return (
    <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
      {STEPS.map((step, i) => (
        <div key={step.title} className="flex items-start gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
          <span className="text-lg">{step.icon}</span>
          <div>
            <p className="text-xs font-semibold text-[var(--text)]">
              {i + 1}. {step.title}
            </p>
            <p className="text-xs text-[var(--text-muted)]">{step.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
