// In local dev this stays empty and Vite's dev-server proxy (see vite.config.ts) forwards
// /api/* to the backend. In production the frontend and backend are separate Render services
// on different origins, so the build needs an absolute backend URL baked in via this env var.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")
