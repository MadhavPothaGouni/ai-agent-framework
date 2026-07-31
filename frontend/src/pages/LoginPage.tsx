import { motion } from "framer-motion"
import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiErrorMessage, login } from "../lib/api"

export function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { setAuthToken } = useAuth()
  const navigate = useNavigate()

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { access_token } = await login(email, password)
      setAuthToken(access_token)
      navigate("/chat")
    } catch (err) {
      setError(apiErrorMessage(err, "Login failed. Check your credentials."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <motion.form
        onSubmit={onSubmit}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="flex w-full max-w-sm flex-col gap-4"
      >
        <div className="mb-2">
          <h1 className="text-2xl font-semibold text-white">Welcome back</h1>
          <p className="mt-1 text-sm text-white/50">Sign in to your agent workspace.</p>
        </div>

        <Field label="Email">
          <input
            type="email"
            required
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
            placeholder="you@example.com"
          />
        </Field>

        <Field label="Password">
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            placeholder="••••••••"
          />
        </Field>

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-lg bg-[var(--color-danger)]/10 px-3 py-2 text-sm text-[var(--color-danger)]"
          >
            {error}
          </motion.p>
        )}

        <button type="submit" disabled={loading} className={submitClass}>
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <p className="text-center text-sm text-white/40">
          No account?{" "}
          <Link to="/signup" className="text-[var(--color-accent-soft)] hover:underline">
            Create one
          </Link>
        </p>
      </motion.form>
    </AuthShell>
  )
}

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-10%] h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-[var(--color-accent)]/20 blur-[120px]" />
      </div>
      <div className="relative flex w-full max-w-sm flex-col items-center">
        <div className="mb-8 flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-accent-soft)] shadow-lg shadow-[var(--color-accent)]/30" />
          <span className="text-base font-semibold text-white">Agent Framework</span>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium uppercase tracking-wider text-white/40">{label}</span>
      {children}
    </label>
  )
}

export const inputClass =
  "rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-[var(--color-accent)]"

export const submitClass =
  "mt-2 rounded-xl bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-soft)] px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-[var(--color-accent)]/25 transition-transform active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
