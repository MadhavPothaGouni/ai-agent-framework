
import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const TOKEN_KEY = "token";
const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

type StepMessage = {
  type: "step";
  agent: string;
  output: string;
  success: boolean;
};

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

type ServerMessage = StepMessage | DoneMessage | ErrorMessage;

type Status = "idle" | "connecting" | "running" | "done" | "error";

const AGENT_LABELS: Record<string, string> = {
  planner: "Planner",
  coder: "Coder",
  tester: "Tester",
  debugger: "Debugger",
  security_auditor: "Security Auditor",
  reviewer: "Reviewer",
};

function wsUrlFor(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export default function WorkflowPage() {
  const [task, setTask] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [steps, setSteps] = useState<StepMessage[]>([]);
  const [result, setResult] = useState<DoneMessage | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const runWorkflow = () => {
    if (!task.trim() || status === "connecting" || status === "running") return;

    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setStatus("error");
      setErrorMessage("You're not logged in — no auth token found.");
      return;
    }

    setSteps([]);
    setResult(null);
    setErrorMessage(null);
    setStatus("connecting");

    const socket = new WebSocket(wsUrlFor(`/workflow/ws/run?token=${encodeURIComponent(token)}`));
    socketRef.current = socket;

    socket.onopen = () => {
      setStatus("running");
      socket.send(JSON.stringify({ task }));
    };

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ServerMessage;

      if (msg.type === "step") {
        setSteps((prev) => [...prev, msg]);
      } else if (msg.type === "done") {
        setResult(msg);
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
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Run a workflow</h1>
        <p className="mt-1 text-sm text-gray-500">
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
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-gray-500 focus:outline-none disabled:bg-gray-100"
        />
        <button
          onClick={runWorkflow}
          disabled={isBusy || !task.trim()}
          className="rounded-lg bg-gray-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {isBusy ? "Running…" : "Run"}
        </button>
      </div>

      {status === "error" && errorMessage && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="flex flex-col gap-3">
        <AnimatePresence initial={false}>
          {steps.map((step, i) => (
            <motion.div
              key={`${step.agent}-${i}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className={`rounded-lg border px-4 py-3 shadow-sm ${
                step.success ? "border-gray-200 bg-white" : "border-amber-200 bg-amber-50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900">
                  {AGENT_LABELS[step.agent] ?? step.agent}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    step.success ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {step.success ? "OK" : "flagged"}
                </span>
              </div>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-xs text-gray-600">
                {step.output}
              </pre>
            </motion.div>
          ))}
        </AnimatePresence>

        {status === "connecting" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-lg border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-400"
          >
            Connecting…
          </motion.div>
        )}
      </div>

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg border px-4 py-4 text-sm font-medium ${
              result.final_decision === "approved"
                ? "border-green-200 bg-green-50 text-green-800"
                : "border-amber-200 bg-amber-50 text-amber-800"
            }`}
          >
            Final decision: {result.final_decision} · {result.attempts} attempt
            {result.attempts === 1 ? "" : "s"} · run {result.run_id.slice(0, 8)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}