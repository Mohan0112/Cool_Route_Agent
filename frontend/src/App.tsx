import { Hero } from "@/components/landing/Hero"
import { NavBar } from "@/components/layout/NavBar"
import { CoolRoutePage } from "@/pages/CoolRoutePage"

function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />
      <Hero />
      {/* id is the target the hero's CTA and scroll cue jump to. scroll-mt clears the
          sticky NavBar, which would otherwise sit on top of the page heading. */}
      <div id="app" className="flex-1 scroll-mt-14">
        <CoolRoutePage />
      </div>
      <footer className="border-t border-[var(--border)] py-4 text-center text-xs text-[var(--text-muted)]">
        Powered by Google Gemini &middot; FortyGuard Temperature API &middot; Google Maps &middot; OSRM
      </footer>
    </div>
  )
}

export default App
