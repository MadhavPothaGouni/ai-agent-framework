import axios, { AxiosError } from "axios"
import type {
  ApiErrorBody,
  ChatResponse,
  TokenResponse,
  WorkflowResponse,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./types"

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"

export const client = axios.create({ baseURL })

const TOKEN_KEY = "agent_framework_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** Turns any axios error into a readable message from the FastAPI `detail` field. */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong."): string {
  const axiosErr = err as AxiosError<ApiErrorBody>
  return axiosErr?.response?.data?.detail || axiosErr?.message || fallback
}

export async function signup(email: string, password: string): Promise<TokenResponse> {
  const res = await client.post<TokenResponse>("/auth/signup", { email, password })
  return res.data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await client.post<TokenResponse>("/auth/login", { email, password })
  return res.data
}

export async function sendChat(message: string, sessionId?: string): Promise<ChatResponse> {
  const res = await client.post<ChatResponse>("/chat", {
    message,
    session_id: sessionId,
  })
  return res.data
}

export async function runWorkflow(task: string): Promise<WorkflowResponse> {
  const res = await client.post<WorkflowResponse>("/workflow/run", { task })
  return res.data
}

export async function listWorkflowRuns(): Promise<WorkflowRunSummary[]> {
  const res = await client.get<WorkflowRunSummary[]>("/workflow/runs")
  return res.data
}

export async function getWorkflowRun(runId: string): Promise<WorkflowRunDetail> {
  const res = await client.get<WorkflowRunDetail>(`/workflow/runs/${runId}`)
  return res.data
}
