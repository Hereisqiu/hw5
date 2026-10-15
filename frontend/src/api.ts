// Typed client for the FastAPI backend (backend/main.py).

export const API_BASE: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export type Actor = AgentName | 'human'

export interface Approval {
  id: number
  ticket_id: number | null
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number | null
  vendor_id: number | null
  sku: string | null
  size: string | null
  qty: number | null
  amount: number
  account: string
  reason: string
  requested_by: string
  status: 'pending' | 'paid' | 'rejected' | 'refused'
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  payment_id: number | null
}

export interface Draft {
  id: number
  ticket_id: number
  recipient: string
  subject: string
  body: string
  author: string
  status: string
  created_at: string
}

export interface BossDecision {
  ticket_id: number
  status: string
  decision: string
  agents_involved: AgentName[]
  approval_ids: number[]
  draft_ids: number[]
  depends_on: string[]
  open_issues: string[]
}

export interface LastRun {
  run_id: string
  state: 'running' | 'done' | 'error'
  started_at: string
  finished_at?: string
  decision?: BossDecision
  error?: string
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: 'open' | 'in_progress' | 'waiting_approval' | 'resolved'
  notes: string | null
  created_at: string
  running: boolean
  drafts: Draft[]
  approvals: Approval[]
  last_run: LastRun | null
}

export interface AgentEvent {
  seq: number
  timestamp: string
  run_id: string
  ticket_id: number | null
  agent: Actor
  depth: number
  chain: AgentName[]
  step: number
  event:
    | 'start' | 'model_response' | 'tool_call' | 'tool_result' | 'retry'
    | 'delegate' | 'finish' | 'error' | 'human_decision' | 'reset'
  detail: Record<string, any>
  usage: { requests?: number; tool_calls?: number; total_tokens?: number }
  message: string
}

export interface EventsPage {
  events: AgentEvent[]
  next: number
  running: { run_id: string; ticket_id: number } | null
}

export interface Payment {
  id: number
  kind: string
  ref_id: number
  amount: number
  account: string
  paid_at: string
  approved_by: string
}

export interface Cash {
  today: string
  checking: {
    account: string
    balance: number
    pending_approvals: number
    pending_total: number
    balance_if_all_pending_paid: number
  }
  payments: Payment[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return body as T
}

export const api = {
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTicket: (id: number) => request<{ run_id: string }>(`/api/tickets/${id}/run`, { method: 'POST' }),
  events: (since: number) => request<EventsPage>(`/api/events?since=${since}&limit=5000`),
  approve: (id: number, approved_by: string) =>
    request(`/api/approvals/${id}/approve`, { method: 'POST', body: JSON.stringify({ approved_by }) }),
  reject: (id: number, rejected_by: string, reason: string) =>
    request(`/api/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify({ rejected_by, reason }) }),
  cash: () => request<Cash>('/api/cash'),
  reset: () => request<{ reset: boolean }>('/api/reset', { method: 'POST' }),
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
