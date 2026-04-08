/** Backend base URL. Set VITE_API_URL in frontend/.env (local) or Vercel env (production). */
const raw = import.meta.env.VITE_API_URL || "http://localhost:8000"
export const API_BASE = String(raw).replace(/\/$/, "")
