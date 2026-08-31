import { useCallback, useMemo, useState } from "react"
import { GoogleMap, useJsApiLoader, Polyline, Marker, InfoWindow } from "@react-google-maps/api"
import type { RouteOption } from "@/lib/types"

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? ""

const PALETTE: Record<string, string> = {
  coolest: "#2563eb",
  fastest: "#ea580c",
  balanced: "#7c3aed",
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
  height?: number | string
}

const DEFAULT_CENTER = { lat: 33.4484, lng: -112.074 }

const MAP_OPTIONS: google.maps.MapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  streetViewControl: false,
  mapTypeControl: false,
  fullscreenControl: true,
  styles: [
    // Slightly soften the map for a cleaner look with colored route overlays
    { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] },
    { featureType: "transit", elementType: "labels.icon", stylers: [{ visibility: "off" }] },
  ],
}

/** Fits the map viewport to show every route with comfortable padding. */
function useFitBounds(options: RouteOption[]) {
  return useCallback(
    (map: google.maps.Map) => {
      const allPoints = options.flatMap((o) => o.geometry)
      if (allPoints.length === 0) return

      const bounds = new google.maps.LatLngBounds()
      for (const [lat, lng] of allPoints) {
        bounds.extend({ lat, lng })
      }
      map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 })
    },
    [options]
  )
}

export function RouteMap({ options, originLabel, destinationLabel, height = 420 }: RouteMapProps) {
  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: GOOGLE_MAPS_API_KEY })

  const [activeInfo, setActiveInfo] = useState<{
    position: google.maps.LatLngLiteral
    content: string
  } | null>(null)

  const firstGeometry = options.find((o) => o.geometry.length > 0)?.geometry
  const origin = firstGeometry ? { lat: firstGeometry[0][0], lng: firstGeometry[0][1] } : null
  const destination = firstGeometry
    ? { lat: firstGeometry[firstGeometry.length - 1][0], lng: firstGeometry[firstGeometry.length - 1][1] }
    : null

  const fitBounds = useFitBounds(options)

  // Convert each route's [lat, lng] geometry to Google Maps LatLngLiteral[]
  const routePaths = useMemo(
    () =>
      options.map((o) => ({
        routeId: o.route_id,
        path: o.geometry.map(([lat, lng]) => ({ lat, lng })),
        label: o.label,
        info: o,
      })),
    [options]
  )

  if (!isLoaded) {
    return (
      <div
        style={{ height, width: "100%" }}
        className="flex items-center justify-center bg-[var(--surface-2)] text-sm text-[var(--text-muted)]"
      >
        Loading map…
      </div>
    )
  }

  return (
    <GoogleMap
      mapContainerStyle={{ height, width: "100%" }}
      center={DEFAULT_CENTER}
      zoom={12}
      onLoad={fitBounds}
      options={MAP_OPTIONS}
    >
      {/* Route polylines */}
      {routePaths.map((route, i) => (
        <Polyline
          key={route.routeId}
          path={route.path}
          options={{
            strokeColor: routeColor(route.label, i),
            strokeWeight: 5,
            strokeOpacity: 0.85,
          }}
          onClick={() => {
            const mid = route.path[Math.floor(route.path.length / 2)]
            const o = route.info
            setActiveInfo({
              position: mid,
              content: [
                `<strong>${o.label}</strong>`,
                `${o.distance_km.toFixed(1)} km · ${o.duration_min.toFixed(0)} min`,
                `Mean ${o.mean_temp_c.toFixed(1)}°C (max ${o.max_temp_c.toFixed(1)}°C)`,
                o.mean_solar_irradiance_wm2 != null
                  ? `Sun exposure: ${o.mean_solar_irradiance_wm2.toFixed(0)} W/m²`
                  : "",
                o.risk_category ? `Risk: ${o.risk_category}` : "",
              ]
                .filter(Boolean)
                .join("<br/>"),
            })
          }}
        />
      ))}

      {/* Origin marker (green) */}
      {origin && (
        <Marker
          position={origin}
          label={{ text: "A", color: "#fff", fontWeight: "bold", fontSize: "13px" }}
          icon={{
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: "#16a34a",
            fillOpacity: 1,
            strokeColor: "#fff",
            strokeWeight: 2,
          }}
          onClick={() =>
            setActiveInfo({ position: origin, content: `<strong>Start:</strong> ${originLabel ?? "Origin"}` })
          }
        />
      )}

      {/* Destination marker (red) */}
      {destination && (
        <Marker
          position={destination}
          label={{ text: "B", color: "#fff", fontWeight: "bold", fontSize: "13px" }}
          icon={{
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: "#dc2626",
            fillOpacity: 1,
            strokeColor: "#fff",
            strokeWeight: 2,
          }}
          onClick={() =>
            setActiveInfo({
              position: destination,
              content: `<strong>End:</strong> ${destinationLabel ?? "Destination"}`,
            })
          }
        />
      )}

      {/* Info window (shared — one open at a time, like Google Maps) */}
      {activeInfo && (
        <InfoWindow position={activeInfo.position} onCloseClick={() => setActiveInfo(null)}>
          <div
            style={{ fontSize: "13px", lineHeight: "1.5", color: "#1a1a1a" }}
            dangerouslySetInnerHTML={{ __html: activeInfo.content }}
          />
        </InfoWindow>
      )}
    </GoogleMap>
  )
}
