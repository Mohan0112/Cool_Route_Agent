import { Badge } from "@/components/ui/Badge"
import type { StreamStatus } from "@/hooks/useAgentStream"

const LABELS: Record<StreamStatus, string> = {
  idle: "Idle",
  streaming: "Running…",
  succeeded: "Succeeded",
  failed: "Failed",
}

export function StatusBadge({ status }: { status: StreamStatus }) {
  const tone = status === "succeeded" ? "success" : status === "failed" ? "danger" : status === "streaming" ? "accent" : "neutral"
  return <Badge tone={tone}>{LABELS[status]}</Badge>
}
