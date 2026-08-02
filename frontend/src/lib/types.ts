export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ChatResponse {
  reply: string
  session_id: string
}

export type AgentName = "planner" | "coder" | "tester" | "debugger" | "security_auditor" | "human_review" | "reviewer";

export interface WorkflowStep {
  agent: AgentName
  output: string
  success: boolean
}

export interface WorkflowResponse {
  run_id: string
  steps: WorkflowStep[]
  final_decision: string
  attempts: number
}

export interface WorkflowRunSummary {
  run_id: string
  task: string
  final_decision: string
  attempts: number
  created_at: string
}

export interface WorkflowRunDetail extends WorkflowRunSummary {
  steps: WorkflowStep[]
}

export interface ApiErrorBody {
  detail?: string
}
