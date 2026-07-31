import { motion } from "framer-motion"
import { useState, type FormEvent } from "react"
import { AgentPipeline } from "../components/AgentPipeline"
import { Loader } from "../components/Loader"
import { apiErrorMessage, runWorkflow } from "../lib/api"
import type { WorkflowResponse } from "../lib/types"

export function WorkflowPage() {
  const [task, setTask] = useState("")
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<WorkflowResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const trimmed = task.trim()
    if (!trimmed || running) return

    setError(null)
    setResult(null)
    setRunning(true)
    try {
      const res = await runWorkflow(trimmed)
      setResult(res)
    } catch (err) {
      setError(apiErrorMessage(err, "Workflow run failed."))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-6 py-8">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-white">Run a workflow</h1>
        <p className="text-sm text-white/40">
          Planner → Coder → Tester → Reviewer, with a real retry loop if tests fail.
        </p>
      </div>

      <form onSubmit={onSubmit} className="mb-6 flex flex-col gap-3">
        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Describe a task, e.g. build a function that reverses a string"
          rows={3}
          className="resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-[var(--color-accent)]"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-white/30">
            {running ? "Agents are working on this…" : " "}
          </p>
          <button
            type="submit"
            disabled={running || !task.trim()}
            className="rounded-xl bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-soft)] px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-[var(--color-accent)]/25 transition-transform active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running ? "Running…" : "Run workflow"}
          </button>
        </div>
      </form>

      {error && (
        <p className="mb-4 rounded-lg bg-[var(--color-danger)]/10 px-3 py-2 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <div className="flex-1 overflow-y-auto pb-8">
        {running && (
          <div className="flex items-center gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-4">
            <Loader label="Planner is thinking…" />
          </div>
        )}

        {result && !running && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <AgentPipeline
              steps={result.steps}
              finalDecision={result.final_decision}
              attempts={result.attempts}
            />
          </motion.div>
        )}

        {!result && !running && !error && (
          <div className="flex h-40 items-center justify-center text-sm text-white/25">
            Describe a task above and watch the agents work.
          </div>
        )}
      </div>
    </div>
  )
}
