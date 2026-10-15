import { TICKET_KIND } from '../agents'
import type { Ticket } from '../api'

const STATUS_LABEL: Record<Ticket['status'], string> = {
  open: 'Open',
  in_progress: 'In progress',
  waiting_approval: 'Awaiting approval',
  resolved: 'Resolved',
}

export function isResolved(t: Ticket) {
  return t.status === 'resolved' || t.last_run?.state === 'done'
}

function detailLine(t: Ticket) {
  if (t.sku) return `${t.qty} × ${t.sku} · size ${t.size}`
  if (t.lease_id) return `Lease #${t.lease_id}`
  return t.subject
}

/** The three tickets as cards on a board. */
export function TicketBoard({ tickets, selected, onSelect, onRun, busy }: {
  tickets: Ticket[]
  selected: number | null
  onSelect: (id: number) => void
  onRun: (id: number) => void
  busy: boolean
}) {
  return (
    <div className="board">
      {tickets.map(t => {
        const kind = TICKET_KIND[t.type] ?? { tag: t.type, glyph: '•' }
        const pending = t.approvals.filter(a => a.status === 'pending').length
        const resolved = isResolved(t)
        const state = t.running ? 'running' : resolved ? 'resolved' : t.last_run?.state === 'error' ? 'error' : 'open'
        return (
          <article key={t.id} className={`ticket ${state} ${selected === t.id ? 'selected' : ''}`}
            onClick={() => onSelect(t.id)}>
            <div className="ticket-top">
              <span className="ticket-glyph">{kind.glyph}</span>
              <span className="ticket-id">#{t.id}</span>
              <span className="ticket-kind">{kind.tag}</span>
            </div>
            <h3>{t.subject}</h3>
            <p className="ticket-who">{t.requester}</p>
            <p className="ticket-detail">{detailLine(t)}</p>
            <div className="ticket-chips">
              <span className={`chip status-${t.status}`}>{STATUS_LABEL[t.status]}</span>
              {pending > 0 && <span className="chip chip-approval">{pending} to approve</span>}
              {t.drafts.length > 0 && <span className="chip chip-draft">{t.drafts.length} draft</span>}
            </div>
            {t.running && <div className="run-stripe"><span>Crew at work</span></div>}
            {resolved && !t.running && <div className="stamp">Resolved</div>}
            {state === 'error' && <p className="ticket-error">Run stopped: {t.last_run?.error}</p>}
            <button className="run-btn" disabled={busy}
              onClick={ev => { ev.stopPropagation(); onRun(t.id) }}>
              {t.running ? 'Running…' : t.last_run ? 'Run again' : 'Send the crew'}
            </button>
          </article>
        )
      })}
    </div>
  )
}
