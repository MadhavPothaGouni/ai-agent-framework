import { motion } from "framer-motion"
import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiErrorMessage, signup } from "../lib/api"
import { AuthShell, Field, inputClass, submitClass } from "./LoginPage"

export function SignupPage() {
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
      const { access_token } = await signup(email, password)
      setAuthToken(access_token)
      navigate("/chat")
    } catch (err) {
      setError(apiErrorMessage(err, "Signup failed. That email may already be in use."))
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
          <h1 className="text-2xl font-semibold text-white">Create your account</h1>
          <p className="mt-1 text-sm text-white/50">Start building with the agent framework.</p>
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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            placeholder="At least 8 characters"
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
          {loading ? "Creating account…" : "Create account"}
        </button>

        <p className="text-center text-sm text-white/40">
          Already have an account?{" "}
          <Link to="/login" className="text-[var(--color-accent-soft)] hover:underline">
            Sign in
          </Link>
        </p>
      </motion.form>
    </AuthShell>
  )
}
