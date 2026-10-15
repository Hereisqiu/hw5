import { useState } from 'react'
import { AGENTS } from '../agents'
import { money, type Actor, type Approval } from '../api'
import { Critter } from './Critter'

function title(a: Approval) {
  if (a.kind === 'invoice') return `Pay invoice #${a.ref_id}`
  if (a.kind === 'rent') return `Pay rent · lease #${a.ref_id}`
  return `Purchase order · ${a.qty} × ${a.sku} ${a.size}`
}

/** Human approval queue: the only place money can move. */
export function ApprovalInbox({ approvals, balance, approver, setApprover, onApprove, onReject }: {
  approvals: Approval[]
  balance: number
  approver: string
  setApprover: (s: string) => void
  onApprove: (a: Approval) => Promise<void>
  onReject: (a: Approval, reason: string) => Promise<void>
}) {
  const [rejecting, setRejecting] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [working, setWorking] = useState<number | null>(null)
  const pending = approvals.filter(a => a.status === 'pending')
  const decided = approvals.filter(a => a.status !== 'pending').slice(-4).reverse()
  const named = approver.trim().length > 0

  const act = async (id: number, fn: () => Promise<void>) => {
    setWorking(id)
    try { await fn() } finally { setWorking(null) }
  }

  return (
    <div className="inbox">
      <label className="approver">
        <span>Approving as</span>
        <input value={approver} placeholder="Your name" onChange={e => setApprover(e.target.value)} />
      </label>
      {pending.length === 0 && <p className="muted inbox-empty">No payments waiting. Agents can only prepare them, and you pay.</p>}
      {pending.map(a => {
        const after = balance - a.amount
        const who = (a.requested_by in AGENTS ? a.requested_by : 'accounting') as Actor
        return (
          <div key={a.id} className={`approval kind-${a.kind}`}>
            <div className="approval-head">
              <span className="approval-title">{title(a)}</span>
              <span className="approval-amount">{money(a.amount)}</span>
            </div>
            <div className="approval-meta">
              <Critter agent={who} size={20} /> requested by {AGENTS[who].label} · ticket #{a.ticket_id} · approval #{a.id}
            </div>
            <p className="approval-reason">{a.reason}</p>
            <div className={`approval-after ${after < 0 ? 'short' : ''}`}>
              Balance after: <b>{money(after)}</b>{after < 0 && ' — not enough cash, will be refused'}
            </div>
            {rejecting === a.id ? (
              <div className="reject-form">
                <input autoFocus value={reason} placeholder="Why reject?" onChange={e => setReason(e.target.value)} />
                <button className="btn ghost" onClick={() => setRejecting(null)}>Cancel</button>
                <button className="btn danger" disabled={!reason.trim() || !named || working === a.id}
                  onClick={() => act(a.id, async () => { await onReject(a, reason); setRejecting(null); setReason('') })}>
                  Reject
                </button>
              </div>
            ) : (
              <div className="approval-actions">
                <button className="btn ghost" disabled={working === a.id} onClick={() => setRejecting(a.id)}>Reject</button>
                <button className="btn primary" disabled={!named || working === a.id}
                  title={named ? '' : 'Type your name first'}
                  onClick={() => act(a.id, () => onApprove(a))}>
                  {working === a.id ? 'Paying…' : 'Approve & pay'}
                </button>
              </div>
            )}
          </div>
        )
      })}
      {decided.length > 0 && (
        <div className="decided">
          {decided.map(a => (
            <div key={a.id} className={`decided-row ${a.status}`}>
              <span>#{a.id} {title(a)}</span>
              <span>{a.status === 'paid' ? `−${money(a.amount)}` : a.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
