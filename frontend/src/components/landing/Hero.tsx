import { useEffect, useState } from "react"

/** How long each slide stays up before the carousel advances. */
const ROTATE_MS = 5000

/** The id the CTA and the scroll cue jump to -- App.tsx puts this on the app section. */
const APP_ANCHOR = "app"

/**
 * Swap these `image` values for local files (e.g. "/cycling.jpg" dropped into public/)
 * whenever better photography turns up -- nothing else in this file needs to change.
 * Currently hotlinked from the Unsplash CDN under the free Unsplash License.
 */
const SLIDES = [
  {
    id: "cycling",
    eyebrow: "For cyclists",
    headline: "Ride the shady side.",
    body: "Two routes can be the same distance and still be degrees apart. Sundodger measures the real heat along each one and points you down the cooler street.",
    image: "https://images.unsplash.com/photo-1652348588909-e3c66c7e95f7?q=75&w=1920&auto=format&fit=crop",
    credit: "Fons Heijnsbroek",
    creditUrl: "https://unsplash.com/photos/a-person-riding-a-bicycle-down-a-busy-street-wlc2B1Kd9Ig",
    /** object-position, so the subject survives the crop at every viewport width. */
    focus: "50% 45%",
  },
  {
    id: "commute",
    eyebrow: "For commuters",
    headline: "Get to the office without the sweat.",
    body: "Plan the walk from the station to your desk around the midday sun -- then check whether leaving half an hour later is cooler.",
    image: "https://images.unsplash.com/photo-1766126535244-b75a7b8d511d?q=75&w=1920&auto=format&fit=crop",
    credit: "niko linh",
    creditUrl: "https://unsplash.com/photos/people-walking-on-a-busy-city-street-sidewalk-CqDEv2KDt3E",
    focus: "50% 40%",
  },
  {
    id: "logistics",
    eyebrow: "For drivers & delivery",
    headline: "Keep crews and cargo cooler.",
    body: "Couriers, last-mile fleets and freight operators can pick the route and the departure window that cut cab heat and cargo risk.",
    image: "https://images.unsplash.com/photo-1720811559337-c59b75acc4de?q=75&w=1920&auto=format&fit=crop",
    credit: "Tom Jackson",
    creditUrl: "https://unsplash.com/photos/a-semi-truck-driving-down-the-road-in-the-desert-Rhwj3CPwc6o",
    focus: "50% 55%",
  },
] as const

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"

function usePrefersReducedMotion() {
  // Read the initial value lazily during the first render rather than assuming false and
  // correcting it in an effect -- that spared a cascading re-render and, more importantly,
  // meant someone with reduced motion on never saw a frame of animation before it stopped.
  const [reduced, setReduced] = useState(() => window.matchMedia(REDUCED_MOTION_QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(REDUCED_MOTION_QUERY)
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [])
  return reduced
}

function scrollToApp() {
  document.getElementById(APP_ANCHOR)?.scrollIntoView({ behavior: "smooth", block: "start" })
}

export function Hero() {
  const [index, setIndex] = useState(0)
  // A photo that 404s, or that a demo machine with no wifi can never reach, would leave the
  // headline sitting on a blank rectangle. Tracking failures lets the brand gradient show
  // through instead, which still reads as intentional.
  const [failed, setFailed] = useState<Record<string, boolean>>({})
  const reducedMotion = usePrefersReducedMotion()

  // Rotates unconditionally. Two earlier guards each silently froze the carousel: pausing
  // on hover (the hero is full-viewport, so the cursor is always inside it) and bailing out
  // under prefers-reduced-motion (Windows "show animations: off" sets that, and it killed
  // the rotation outright). Reduced motion now only suppresses the decorative zoom/bob --
  // advancing the slide is the feature itself, not an embellishment.
  // Keyed on `index` rather than started once, so picking a dot restarts the dwell time
  // instead of cutting the slide you just chose short.
  useEffect(() => {
    const timer = setTimeout(() => setIndex((i) => (i + 1) % SLIDES.length), ROTATE_MS)
    return () => clearTimeout(timer)
  }, [index])

  const active = SLIDES[index]

  return (
    <section
      aria-roledescription="carousel"
      aria-label="What you can use Sundodger for"
      className="relative isolate flex min-h-[calc(100svh-3.5rem)] items-center overflow-hidden bg-[#160f06]"
    >
      {/* Brand-tinted ground -- also what shows if a photo never arrives. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-20"
        style={{
          background:
            "radial-gradient(120% 90% at 75% 15%, rgba(249,115,22,0.30) 0%, transparent 60%), linear-gradient(160deg, #2a1a08 0%, #140d05 100%)",
        }}
      />

      {SLIDES.map((slide, i) => {
        const isActive = i === index
        return (
          <div
            key={slide.id}
            aria-hidden={!isActive}
            className={
              "absolute inset-0 -z-10 transition-opacity duration-1000 ease-out " +
              (isActive ? "opacity-100" : "opacity-0")
            }
          >
            {!failed[slide.id] && (
              <img
                src={slide.image}
                alt=""
                /* The first slide is what a visitor actually sees on load, so it must not be
                   deferred; the other two prefetch quietly for a seamless first crossfade. */
                loading={i === 0 ? "eager" : "lazy"}
                fetchPriority={i === 0 ? "high" : "low"}
                decoding="async"
                onError={() => setFailed((prev) => ({ ...prev, [slide.id]: true }))}
                className="h-full w-full object-cover"
                style={{
                  objectPosition: slide.focus,
                  animation: isActive && !reducedMotion ? "sd-kenburns 14s ease-out both" : undefined,
                }}
              />
            )}
            {/* Scrim: heavy on the left where the copy sits, light on the right so the
                photograph is still legible as a photograph. */}
            <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/45 to-black/15" />
            <div aria-hidden="true" className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/65 to-transparent" />
          </div>
        )
      })}

      <div className="mx-auto w-full max-w-6xl px-6 py-24">
        <div
          /* Remounting on slide change replays the entrance animation for the new copy, so
             the text feels like it arrives with its photo rather than swapping underneath it. */
          key={active.id}
          className="max-w-2xl"
          style={{ animation: reducedMotion ? undefined : "sd-rise 700ms cubic-bezier(0.22,1,0.36,1) both" }}
        >
          <span className="inline-flex items-center rounded-full border border-white/25 bg-white/10 px-3 py-1 text-xs font-medium tracking-wide text-white/90 uppercase backdrop-blur">
            {active.eyebrow}
          </span>
          <h1 className="mt-5 text-4xl leading-[1.05] font-semibold tracking-tight text-balance text-white sm:text-5xl lg:text-6xl">
            {active.headline}
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-white/80 sm:text-lg">{active.body}</p>

          <div className="mt-9 flex flex-wrap items-center gap-x-4 gap-y-3">
            <button
              type="button"
              onClick={scrollToApp}
              className="inline-flex items-center gap-2 rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-black/30 transition hover:bg-[var(--accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
            >
              Plan your route
              <span aria-hidden="true">&darr;</span>
            </button>
            <span className="text-xs text-white/60">
              Measured heat, not estimates &middot; walking, cycling &amp; driving
            </span>
          </div>
        </div>
      </div>

      {/* Slide picker -- real buttons rather than dots-as-divs, so it is keyboard-operable. */}
      <div className="absolute bottom-8 left-0 w-full">
        <div className="mx-auto flex max-w-6xl items-end justify-between gap-6 px-6">
          <div className="flex items-center gap-3">
            {SLIDES.map((slide, i) => (
              <button
                key={slide.id}
                type="button"
                onClick={() => setIndex(i)}
                aria-label={"Show slide: " + slide.headline}
                aria-current={i === index}
                className="group py-2"
              >
                <span
                  className={
                    "block h-1 overflow-hidden rounded-full transition-all duration-500 " +
                    (i === index ? "w-16 bg-white/30" : "w-8 bg-white/25 group-hover:bg-white/55")
                  }
                >
                  {i === index && (
                    <span
                      key={index}
                      className="block h-full rounded-full bg-white"
                      style={{ animation: "sd-progress " + ROTATE_MS + "ms linear both" }}
                    />
                  )}
                </span>
              </button>
            ))}
          </div>

          <a
            href={active.creditUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="hidden text-[11px] text-white/45 transition hover:text-white/80 sm:block"
          >
            Photo: {active.credit} / Unsplash
          </a>
        </div>
      </div>

      {/* Scroll cue. A bare low-contrast arrow read as decoration against a dark photo, so
          this is now an unmistakable control: labelled, accent-filled, and haloed by a
          pulsing ring that points at the one thing a first-time visitor needs to do next. */}
      <button
        type="button"
        onClick={scrollToApp}
        aria-label="Scroll down to the route planner"
        className="group absolute bottom-20 left-1/2 flex -translate-x-1/2 flex-col items-center gap-2 rounded-2xl px-3 py-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80 sm:bottom-6"
      >
        <span className="text-[11px] font-semibold tracking-[0.18em] text-white/75 uppercase transition group-hover:text-white">
          See it work
        </span>
        <span
          className="relative flex h-11 w-11 items-center justify-center"
          style={{ animation: reducedMotion ? undefined : "sd-bob 1.8s ease-in-out infinite" }}
        >
          {!reducedMotion && (
            <span
              aria-hidden="true"
              className="absolute inset-0 rounded-full border-2 border-[var(--accent)]"
              style={{ animation: "sd-halo 2.2s ease-out infinite" }}
            />
          )}
          <span className="relative flex h-11 w-11 items-center justify-center rounded-full border-2 border-white/70 bg-[var(--accent)] text-lg font-bold text-white shadow-lg shadow-black/40 transition group-hover:border-white group-hover:bg-[var(--accent-hover)]">
            <span aria-hidden="true" className="-mt-0.5 leading-none">
              &darr;
            </span>
          </span>
        </span>
      </button>
    </section>
  )
}
