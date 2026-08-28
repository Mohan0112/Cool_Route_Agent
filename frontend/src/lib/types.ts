export type SseEventType =
  | "run_started"
  | "tool_call"
  | "tool_result"
  | "tool_error"
  | "progress"
  | "final"
  | "error"
  | "run_finished"

export interface TraceEvent {
  seq: number
  type: SseEventType
  data: Record<string, unknown>
}

export type TravelMode = "walking" | "cycling" | "driving"

export interface RouteOption {
  route_id: number
  label: string
  distance_km: number
  duration_min: number
  mean_temp_c: number
  max_temp_c: number
  mean_solar_irradiance_wm2: number | null
  rationale: string
  geometry: [number, number][] // [lat, lon] pairs, attached server-side once the agent finishes
  risk_category?: string // attached server-side from max_temp_c, deterministic regardless of model wording
  safety_tip?: string
}

export interface DepartureTimeOption {
  time: string // "HH:MM"
  mean_temp_c: number
  mean_solar_irradiance_wm2: number | null
}

export interface CoolRoutePlan {
  origin_label: string
  destination_label: string
  mode: TravelMode
  summary: string
  options: RouteOption[]
  measured_outcome: string
  sources: string[]
  caveats?: string | null
  departure_time_comparison?: DepartureTimeOption[] | null
}

export interface UsageSummary {
  credit_summary?: {
    total_available_credits?: number
    cycle_credits_used?: number
    cycle_remaining_credits?: number
  }
  demo_mode?: boolean
}
