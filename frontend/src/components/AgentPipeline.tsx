import { motion } from "framer-motion"
import { useState } from "react"
import type { AgentName, WorkflowStep } from "../lib/types"

const AGENT_META: Record<AgentName, { label: string; color: string; icon: string }> = {
  planner: { label: "Planner", color: "#7c5cff", icon: "◈" },
  coder: { label: "Coder", color: "#38bdf8", icon: "◇" },
  tester: { label: "Tester", color: "#f59e0b", icon: "◆" },
  debugger: { label: "Debugger", color: "#f43f5e", icon: "◐" },
  security_auditor: { label: "Security Auditor", color: "#14b8a6", icon: "◎" },
  human_review: { label: "Human Review", color: "#6366f1", icon: "◑" },
  reviewer: { label: "Reviewer", color: "#22c55e", icon: "◉" },
}

function attemptLabels(steps: WorkflowStep[]): (number | null)[] {
  let coderCount = 0
  return steps.map((step) => {
    if (step.agent === "coder") {
      coderCount += 1
      return coderCount
    }
    if (step.agent === "tester") return coderCount
    return null
  })
}

export function AgentPipeline({
  steps,
  finalDecision,
  attempts,
}: {
  steps: WorkflowStep[]
  finalDecision: string
  attempts: number
}) {
  const labels = attemptLabels(steps)
  const approved = finalDecision === "approved"

  return (
    <div className="flex flex-col gap-3">
      {steps.map((step, i) => (
        <motion.div
          key={`${step.agent}-${i}`}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08, duration: 0.3, ease: "easeOut" }}
        >
          {(step.agent === "coder" && labels[i] && labels[i]! > 1) && (
            <div className="mb-2 mt-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-white/30">
              <span className="h-px flex-1 bg-white/10" />
              Retry — attempt {labels[i]}
              <span className="h-px flex-1 bg-white/10" />
            </div>
          )}
          <StepCard step={step} />
        </motion.div>
      ))}

      {finalDecision && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: steps.length * 0.08 + 0.1, duration: 0.3 }}
          className={`mt-2 flex items-center justify-between rounded-2xl border px-5 py-4 ${
            approved
              ? "border-[var(--color-success)]/30 bg-[var(--color-success)]/10"
              : "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10"
          }`}
        >
          <div className="flex items-center gap-3">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${
                approved ? "bg-[var(--color-success)]/20" : "bg-[var(--color-danger)]/20"
              }`}
            >
              {approved ? "✓" : "✕"}
            </span>
            <div>
              <div className="text-sm font-semibold text-white">
                {approved ? "Approved" : "Changes requested"}
              </div>
              <div className="text-xs text-white/40">
                {attempts} attempt{attempts === 1 ? "" : "s"}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

function StepCard({ step }: { step: WorkflowStep }) {
  const [expanded, setExpanded] = useState(false)
  const meta = AGENT_META[step.agent]
  const isLong = step.output.length > 160

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-colors hover:border-white/20">
      <div className="flex items-center gap-3">
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm"
          style={{ backgroundColor: `${meta.color}22`, color: meta.color }}
        >
          {meta.icon}
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">{meta.label}</span>
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                step.success ? "bg-[var(--color-success)]" : "bg-[var(--color-danger)]"
              }`}
            />
          </div>
        </div>
        {isLong && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-white/40 transition-colors hover:text-white/70"
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
        )}
      </div>

      <pre
        className={`mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-black/30 p-3 font-mono text-xs leading-relaxed text-white/70 ${
          !expanded && isLong ? "max-h-24 overflow-y-hidden" : ""
        }`}
      >
        {step.output}
      </pre>
    </div>
  )
}