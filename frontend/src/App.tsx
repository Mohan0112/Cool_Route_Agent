import { NavBar } from "@/components/layout/NavBar"
import { CoolRoutePage } from "@/pages/CoolRoutePage"

function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />
      <div className="flex-1">
        <CoolRoutePage />
      </div>
      <footer className="border-t border-[var(--border)] py-4 text-center text-xs text-[var(--text-muted)]">
        Powered by Google Gemini &middot; FortyGuard Temperature API &middot; OSRM &middot; Nominatim/OpenStreetMap
      </footer>
    </div>
  )
}

export default App
