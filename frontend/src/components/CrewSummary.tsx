import { AGENTS, CREW } from '../agents'
import type { Actor, AgentEvent, Ticket } from '../api'
import { Critter } from './Critter'

interface AgentStats {
  tools: Map<string, number>
  delegatedTo: Actor[]
  summary?: string
  writes: string[]
}

const WRITE_TOOLS: Record<string, string> = {
  prepare_payment: 'queued a payment for approval',
  prepare_purchase_order: 'queued a purchase order',
  save_customer_draft: 'saved a customer draft',
  update_ticket: 'updated the ticket',
}

/** One line per agent: what they did on the selected ticket's latest run. */
export function CrewSummary({ events, ticket }: { events: AgentEvent[]; ticket: Ticket | undefined }) {
  const stats = new Map<Actor, AgentStats>()
  const get = (a: Actor) => {
    if (!stats.has(a)) stats.set(a, { tools: new Map(), delegatedTo: [], writes: [] })
    return stats.get(a)!
  }
  for (const e of events) {
    if (e.agent === 'human') continue
    const s = get(e.agent)
    if (e.event === 'tool_call' && !['final_result', 'delegate'].includes(e.detail.tool)) {
      s.tools.set(e.detail.tool, (s.tools.get(e.detail.tool) ?? 0) + 1)
      const w = WRITE_TOOLS[e.detail.tool]
      if (w && !s.writes.includes(w)) s.writes.push(w)
    }
    if (e.event === 'delegate' && !s.delegatedTo.includes(e.detail.to)) s.delegatedTo.push(e.detail.to)
    if (e.event === 'finish') s.summary = e.detail.output?.decision ?? e.detail.output?.summary
  }
  const last = events.at(-1)
  const decision = ticket?.last_run?.decision

  if (stats.size === 0) return <p className="muted">No run yet for this ticket.</p>

  return (
    <div className="summary">
      {decision && (
        <div className="decision-card">
          <div className="decision-label">Boss's call</div>
          <p>{decision.decision}</p>
          {decision.open_issues.length > 0 && (
            <ul>{decision.open_issues.map((x, i) => <li key={i}>{x}</li>)}</ul>
          )}
        </div>
      )}
      {CREW.filter(a => stats.has(a)).map(a => {
        const s = stats.get(a)!
        return (
          <div key={a} className="summary-row" style={{ ['--c' as string]: AGENTS[a].color }}>
            <Critter agent={a} size={30} mood="happy" />
            <div>
              <div className="summary-name">{AGENTS[a].label}
                {s.delegatedTo.length > 0 && <span className="summary-to"> → {s.delegatedTo.map(d => AGENTS[d].label).join(', ')}</span>}
              </div>
              {s.summary && !(a === 'boss' && decision) && <p className="summary-text">{s.summary}</p>}
              <div className="summary-tools">
                {[...s.tools.entries()].map(([t, n]) => <span key={t}>{t}{n > 1 ? ` ×${n}` : ''}</span>)}
              </div>
              {s.writes.length > 0 && <p className="summary-writes">{s.writes.join(' · ')}</p>}
            </div>
          </div>
        )
      })}
      {last?.usage?.total_tokens ? (
        <p className="tokens">{last.usage.requests} model calls · {last.usage.tool_calls} tool calls · {last.usage.total_tokens.toLocaleString()} tokens</p>
      ) : null}
    </div>
  )
}
