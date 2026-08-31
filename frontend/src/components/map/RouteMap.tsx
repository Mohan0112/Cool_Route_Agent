import { useMemo } from "react"
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from "react-leaflet"
import type { RouteOption } from "@/lib/types"

const PALETTE: Record<string, string> = {
  coolest: "#2563eb", // blue -- low temperature
  fastest: "#ea580c", // accent orange -- matches app accent
  balanced: "#7c3aed", // purple
}
const FALLBACK_COLORS = ["#0891b2", "#65a30d", "#db2777"]

export function routeColor(label: string, index: number): string {
  const key = label.trim().toLowerCase()
  for (const [k, color] of Object.entries(PALETTE)) {
    if (key.includes(k)) return color
  }
  return FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

interface RouteMapProps {
  options: RouteOption[]
  originLabel?: string
  destinationLabel?: string
  /** Number for a fixed pixel height, or a CSS length like "100%" to fill the parent. */
  height?: number | string
}

const DEFAULT_CENTER: [number, number] = [33.4484, -112.074] // Phoenix, AZ

export function RouteMap({ options, originLabel, destinationLabel, height = 420 }: RouteMapProps) {
  const firstGeometry = options.find((o) => o.geometry.length > 0)?.geometry
  const origin = firstGeometry?.[0]
  const destination = firstGeometry?.[firstGeometry.length - 1]

  const bounds = useMemo<[[number, number], [number, number]] | null>(() => {
    const allPoints = options.flatMap((o) => o.geometry)
    if (allPoints.length === 0) return null
    const lats = allPoints.map(([la]) => la)
    const lons = allPoints.map(([, lo]) => lo)
    return [
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ]
  }, [options])

  const cartoApiKey = import.meta.env.VITE_CARTO_API_KEY
  const tileUrl = cartoApiKey
    ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${cartoApiKey}`
    : "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"

  return (
    <MapContainer
      center={bounds ? undefined : DEFAULT_CENTER}
      zoom={bounds ? undefined : 12}
      bounds={bounds ?? undefined}
      boundsOptions={{ padding: [32, 32] }}
      scrollWheelZoom={true}
      style={{ height, width: "100%" }}
    >
      <TileLayer
        url={tileUrl}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={20}
        subdomains="abcd"
      />
      {options.map((option, i) => (
        <Polyline
          key={option.route_id}
          positions={option.geometry}
          color={routeColor(option.label, i)}
          weight={5}
          opacity={0.85}
        >
          <Popup>
            <strong>{option.label}</strong>
            <br />
            {option.distance_km.toFixed(1)} km &middot; {option.duration_min.toFixed(0)} min
            <br />
            Mean {option.mean_temp_c.toFixed(1)}&deg;C (max {option.max_temp_c.toFixed(1)}&deg;C)
            {option.mean_solar_irradiance_wm2 != null && (
              <>
                <br />
                Sun exposure: {option.mean_solar_irradiance_wm2.toFixed(0)} W/m&sup2;
              </>
            )}
            {option.risk_category && (
              <>
                <br />
                Risk: {option.risk_category}
              </>
            )}
          </Popup>
        </Polyline>
      ))}
      {origin && (
        <CircleMarker center={origin} radius={8} color="#16a34a" fillColor="#16a34a" fillOpacity={0.9}>
          <Popup>Start: {originLabel ?? "Origin"}</Popup>
        </CircleMarker>
      )}
      {destination && (
        <CircleMarker center={destination} radius={8} color="#dc2626" fillColor="#dc2626" fillOpacity={0.9}>
          <Popup>End: {destinationLabel ?? "Destination"}</Popup>
        </CircleMarker>
      )}
    </MapContainer>
  )
}
