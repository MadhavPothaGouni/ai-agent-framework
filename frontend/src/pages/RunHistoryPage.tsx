import { AnimatePresence, motion } from "framer-motion"
import { useEffect, useState } from "react"
import { AgentPipeline } from "../components/AgentPipeline"
import { Loader } from "../components/Loader"
import { apiErrorMessage, getWorkflowRun, listWorkflowRuns } from "../lib/api"
import type { WorkflowRunDetail, WorkflowRunSummary } from "../lib/types"

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso + "Z").getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function RunHistoryPage() {
  const [runs, setRuns] = useState<WorkflowRunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<WorkflowRunDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    listWorkflowRuns()
      .then(setRuns)
      .catch((err) => setError(apiErrorMessage(err, "Failed to load run history.")))
  }, [])

  const openRun = async (runId: string) => {
    setDetailLoading(true)
    setSelected(null)
    try {
      const detail = await getWorkflowRun(runId)
      setSelected(detail)
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load run detail."))
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-2xl">
          <h1 className="mb-1 text-lg font-semibold text-white">Run history</h1>
          <p className="mb-6 text-sm text-white/40">Every workflow run you've kicked off.</p>

          {error && <p className="mb-4 text-sm text-[var(--color-danger)]">{error}</p>}

          {runs === null && <Loader label="Loading runs…" />}

          {runs?.length === 0 && (
            <div className="rounded-2xl border border-dashed border-[var(--color-border)] px-6 py-10 text-center text-sm text-white/30">
              No runs yet — go run a workflow.
            </div>
          )}

          <div className="flex flex-col gap-2">
            {runs?.map((run, i) => (
              <motion.button
                key={run.run_id}
                onClick={() => openRun(run.run_id)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors ${
                  selected?.run_id === run.run_id
                    ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-white/20"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-white/90">{run.task}</p>
                  <p className="mt-0.5 text-xs text-white/35">
                    {timeAgo(run.created_at)} · {run.attempts} attempt
                    {run.attempts === 1 ? "" : "s"}
                  </p>
                </div>
                <span
                  className={`ml-3 shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
                    run.final_decision === "approved"
                      ? "bg-[var(--color-success)]/15 text-[var(--color-success)]"
                      : "bg-[var(--color-danger)]/15 text-[var(--color-danger)]"
                  }`}
                >
                  {run.final_decision === "approved" ? "Approved" : "Changes requested"}
                </span>
              </motion.button>
            ))}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {(selected || detailLoading) && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="w-[420px] shrink-0 overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-surface)]/40 px-5 py-8 backdrop-blur-xl"
          >
            {detailLoading && <Loader label="Loading run…" />}
            {selected && !detailLoading && (
              <>
                <button
                  onClick={() => setSelected(null)}
                  className="mb-4 text-xs text-white/40 hover:text-white/70"
                >
                  ← Close
                </button>
                <p className="mb-1 text-xs uppercase tracking-wider text-white/30">Task</p>
                <p className="mb-6 text-sm text-white/90">{selected.task}</p>
                <AgentPipeline
                  steps={selected.steps}
                  finalDecision={selected.final_decision}
                  attempts={selected.attempts}
                />
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
