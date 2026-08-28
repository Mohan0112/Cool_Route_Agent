import { useEffect, useState } from "react"
import { api } from "@/lib/api"

interface UsageState {
  demoMode: boolean | null
  remainingCredits: number | null
}

export function useUsage(): UsageState {
  const [state, setState] = useState<UsageState>({ demoMode: null, remainingCredits: null })

  useEffect(() => {
    let cancelled = false
    api
      .getUsage()
      .then((usage) => {
        if (cancelled) return
        setState({
          demoMode: usage.demo_mode ?? null,
          remainingCredits: usage.credit_summary?.cycle_remaining_credits ?? usage.credit_summary?.total_available_credits ?? null,
        })
      })
      .catch(() => {
        if (!cancelled) setState({ demoMode: null, remainingCredits: null })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
