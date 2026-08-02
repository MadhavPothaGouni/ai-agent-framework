
import { useState } from "react";
import { AgentPipeline } from "../components/AgentPipeline";
import type { AgentName, WorkflowStep } from "../lib/types";

const TOKEN_KEY = "agent_framework_token";
const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

type DoneMessage = {
  type: "done";
  run_id: string;
  final_decision: string;
  attempts: number;
};

type ErrorMessage = {
  type: "error";
  message: string;
};

type StepEventMessage = {
  type: "step";
  agent: AgentName;
  output: string;
  success: boolean;
};

type ApprovalRequiredMessage = {
  type: "approval_required";
  approval_id: string;
  agent: string;
  output: string;
};

type ServerMessage = StepEventMessage | DoneMessage | ErrorMessage | ApprovalRequiredMessage;

type Status = "idle" | "connecting" | "running" | "done" | "error";

type PendingApproval = {
  approvalId: string;
  code: string;
};

function wsUrlFor(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function WorkflowPage() {
  const [task, setTask] = useState("");
  const [requireApproval, setRequireApproval] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [finalDecision, setFinalDecision] = useState("");
  const [attempts, setAttempts] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);

  const isBusy = status === "connecting" || status === "running";

  const runWorkflow = () => {
    if (!task.trim() || isBusy) return;

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setStatus("error");
      setErrorMessage("You're not logged in — no auth token found.");
      return;
    }

    setSteps([]);
    setFinalDecision("");
    setAttempts(0);
    setErrorMessage(null);
    setPendingApproval(null);
    setStatus("connecting");

    const ws = new WebSocket(wsUrlFor(`/workflow/ws/run?token=${encodeURIComponent(token)}`));
    setSocket(ws);

    ws.onopen = () => {
      setStatus("running");
      ws.send(JSON.stringify({ task, require_approval: requireApproval }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ServerMessage;

      if (msg.type === "step") {
        setSteps((prev) => [...prev, { agent: msg.agent, output: msg.output, success: msg.success }]);
      } else if (msg.type === "approval_required") {
        setPendingApproval({ approvalId: msg.approval_id, code: msg.output });
      } else if (msg.type === "done") {
        setFinalDecision(msg.final_decision);
        setAttempts(msg.attempts);
        setStatus("done");
      } else if (msg.type === "error") {
        setErrorMessage(msg.message);
        setStatus("error");
      }
    };

    ws.onerror = () => {
      setStatus((current) => (current === "done" ? current : "error"));
      setErrorMessage((current) => current ?? "WebSocket connection error.");
    };

    ws.onclose = () => {
      setStatus((current) => (current === "done" || current === "error" ? current : "error"));
    };
  };

  const decide = (approved: boolean) => {
    if (!socket || !pendingApproval) return;
    socket.send(
      JSON.stringify({
        type: "approval_decision",
        approval_id: pendingApproval.approvalId,
        approved,
      })
    );
    setPendingApproval(null);
  };

  return (
    <div className="flex flex-col gap-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Run a workflow</h1>
        <p className="mt-1 text-sm text-white/40">
          Watch each agent — Planner, Coder, Tester, Debugger, Security Auditor, Reviewer — complete live.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex gap-2">
          <input
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runWorkflow()}
            disabled={isBusy}
            placeholder="e.g. write a function that reverses a string"
            className="flex-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-white placeholder:text-white/30 outline-none transition-colors focus:border-white/30 disabled:opacity-50"
          />
          <button
            onClick={runWorkflow}
            disabled={isBusy || !task.trim()}
            className="rounded-xl bg-[#7c5cff] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#6c4ce6] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isBusy ? "Running…" : "Run"}
          </button>
        </div>

        <label className="flex w-fit items-center gap-2 text-xs text-white/50 select-none">
          <input
            type="checkbox"
            checked={requireApproval}
            disabled={isBusy}
            onChange={(e) => setRequireApproval(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-[var(--color-border)] bg-[var(--color-surface)] accent-[#7c5cff]"
          />
          Require my approval before the Tester executes any generated code
        </label>
      </div>

      {status === "error" && errorMessage && (
        <div className="rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {errorMessage}
        </div>
      )}

      {steps.length > 0 && (
        <AgentPipeline steps={steps} finalDecision={finalDecision} attempts={attempts} />
      )}

      {status === "connecting" && (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] px-4 py-3 text-sm text-white/30">
          Connecting…
        </div>
      )}

      {pendingApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
          <div className="flex max-h-[80vh] w-full max-w-2xl flex-col gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-2xl">
            <div>
              <div className="text-sm font-semibold uppercase tracking-wide text-[#6366f1]">
                Approval required
              </div>
              <h2 className="mt-1 text-lg font-semibold text-white">
                The Coder wants to run this code. Approve it?
              </h2>
              <p className="mt-1 text-xs text-white/40">
                Nothing will execute until you decide — the Tester is paused.
              </p>
            </div>

            <pre className="flex-1 overflow-auto rounded-xl bg-black/40 p-4 font-mono text-xs leading-relaxed text-white/80">
              {pendingApproval.code}
            </pre>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => decide(false)}
                className="rounded-xl border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 px-5 py-2 text-sm font-medium text-[var(--color-danger)] transition-colors hover:bg-[var(--color-danger)]/20"
              >
                Reject
              </button>
              <button
                onClick={() => decide(true)}
                className="rounded-xl bg-[var(--color-success)] px-5 py-2 text-sm font-medium text-black transition-colors hover:opacity-90"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}