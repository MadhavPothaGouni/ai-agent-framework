/**
 * WorkflowPage — runs a DevWorkflow task and streams each agent step live
 * over a WebSocket into the existing <AgentPipeline /> component, instead of
 * blocking on a single POST /workflow/run call until the whole pipeline
 * finishes. Reuses AgentPipeline so styling matches Run History exactly.
 */
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

type ServerMessage = StepEventMessage | DoneMessage | ErrorMessage;

type Status = "idle" | "connecting" | "running" | "done" | "error";

function wsUrlFor(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function WorkflowPage() {
  const [task, setTask] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [finalDecision, setFinalDecision] = useState("");
  const [attempts, setAttempts] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runWorkflow = () => {
    if (!task.trim() || status === "connecting" || status === "running") return;

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
    setStatus("connecting");

    const socket = new WebSocket(wsUrlFor(`/workflow/ws/run?token=${encodeURIComponent(token)}`));

    socket.onopen = () => {
      setStatus("running");
      socket.send(JSON.stringify({ task }));
    };

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ServerMessage;

      if (msg.type === "step") {
        setSteps((prev) => [...prev, { agent: msg.agent, output: msg.output, success: msg.success }]);
      } else if (msg.type === "done") {
        setFinalDecision(msg.final_decision);
        setAttempts(msg.attempts);
        setStatus("done");
      } else if (msg.type === "error") {
        setErrorMessage(msg.message);
        setStatus("error");
      }
    };

    socket.onerror = () => {
      setStatus((current) => (current === "done" ? current : "error"));
      setErrorMessage((current) => current ?? "WebSocket connection error.");
    };

    socket.onclose = () => {
      setStatus((current) => (current === "done" || current === "error" ? current : "error"));
    };
  };

  const isBusy = status === "connecting" || status === "running";

  return (
    <div className="flex flex-col gap-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Run a workflow</h1>
        <p className="mt-1 text-sm text-white/40">
          Watch each agent — Planner, Coder, Tester, Debugger, Security Auditor, Reviewer — complete live.
        </p>
      </div>

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
    </div>
  );
}