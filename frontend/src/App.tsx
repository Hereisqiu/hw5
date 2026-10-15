import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AGENTS, TICKET_KIND } from './agents'
import { api, money, type Actor, type AgentEvent, type Approval, type Cash, type Ticket } from './api'
import { ApprovalInbox } from './components/ApprovalInbox'
import { CashMeter } from './components/CashMeter'
import { Critter } from './components/Critter'
import { CrewMap } from './components/CrewMap'
import { CrewSummary } from './components/CrewSummary'
import { Drafts } from './components/Drafts'
import { LiveFeed } from './components/LiveFeed'
import { TicketBoard, isResolved } from './components/TicketBoard'

type SideTab = 'approvals' | 'summary' | 'drafts'
type Toast = { kind: 'ok' | 'err'; text: string } | null

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [running, setRunning] = useState<{ run_id: string; ticket_id: number } | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [side, setSide] = useState<SideTab>('approvals')
  const [approver, setApproverState] = useState(() => localStorage.getItem('approver') ?? '')
  const [toast, setToast] = useState<Toast>(null)
  const [offline, setOffline] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const next = useRef(0)

  const setApprover = (s: string) => { setApproverState(s); localStorage.setItem('approver', s) }
  const say = (kind: 'ok' | 'err', text: string) => {
    setToast({ kind, text })
    window.setTimeout(() => setToast(null), 4500)
  }

  const refreshBoard = useCallback(async () => {
    const [t, c] = await Promise.all([api.tickets(), api.cash()])
    setTickets(t)
    setCash(c)
    setSelected(s => s ?? t[0]?.id ?? null)
  }, [])

  const pullEvents = useCallback(async () => {
    const since = next.current
    const page = await api.events(since)
    next.current = page.next
    if (page.events.length) {
      setEvents(prev => {
        const last = prev.at(-1)?.seq ?? -1
        return [...prev, ...page.events.filter(e => e.seq >= since && e.seq > last)]
      })
    }
    setRunning(page.running)
    return page
  }, [])

  // Poll fast while the crew is working, slowly otherwise.
  useEffect(() => {
    let stop = false
    let timer = 0
    let tick = 0
    const loop = async () => {
      try {
        const page = await pullEvents()
        if (page.running || page.events.length || tick % 3 === 0) await refreshBoard()
        setOffline(false)
        tick++
        timer = window.setTimeout(() => !stop && loop(), page.running ? 1200 : 3500)
      } catch {
        setOffline(true)
        timer = window.setTimeout(() => !stop && loop(), 4000)
      }
    }
    loop()
    return () => { stop = true; clearTimeout(timer) }
  }, [pullEvents, refreshBoard])

  const ticket = tickets.find(t => t.id === selected)
  const runId = running?.ticket_id === selected ? running.run_id : ticket?.last_run?.run_id

  // Events for the selected ticket's latest run, plus human decisions made after it started.
  const runEvents = useMemo(() => {
    if (!runId) return []
    const first = events.find(e => e.run_id === runId)
    return events.filter(e =>
      e.run_id === runId ||
      (e.event === 'human_decision' && e.ticket_id === selected && first !== undefined && e.seq > first.seq))
  }, [events, runId, selected])

  const isRunning = running !== null && running.ticket_id === selected
  const active: Actor | null = useMemo(() => {
    const agentEvents = runEvents.filter(e => e.agent !== 'human')
    const last = agentEvents.at(-1)
    if (!last) return isRunning ? 'boss' : null
    if (last.event === 'finish' && last.depth > 0) return last.chain[last.chain.length - 2]
    if (last.event === 'delegate') return last.detail.to as Actor
    return last.agent
  }, [runEvents, isRunning])

  const allApprovals = tickets.flatMap(t => t.approvals).sort((a, b) => a.id - b.id)
  const pendingCount = allApprovals.filter(a => a.status === 'pending').length

  const run = async (id: number) => {
    setSelected(id)
    try {
      await api.runTicket(id)
      say('ok', `The crew is on ticket #${id}.`)
      await pullEvents()
      await refreshBoard()
    } catch (e) {
      say('err', (e as Error).message)
    }
  }

  const approve = async (a: Approval) => {
    try {
      const res = await api.approve(a.id, approver.trim()) as { new_balance: number }
      say('ok', `Paid ${money(a.amount)}. Checking is now ${money(res.new_balance)}.`)
    } catch (e) {
      say('err', (e as Error).message)
    }
    await refreshBoard()
  }

  const reject = async (a: Approval, reason: string) => {
    try {
      await api.reject(a.id, approver.trim(), reason)
      say('ok', `Rejected approval #${a.id}. No money moved.`)
    } catch (e) {
      say('err', (e as Error).message)
    }
    await refreshBoard()
  }

  const reset = async () => {
    if (!confirmReset) {
      setConfirmReset(true)
      window.setTimeout(() => setConfirmReset(false), 3000)
      return
    }
    setConfirmReset(false)
    try {
      await api.reset()
      say('ok', 'Working database reset to the original. The audit trail is kept.')
      await refreshBoard()
    } catch (e) {
      say('err', (e as Error).message)
    }
  }

  const resolvedCount = tickets.filter(isResolved).length
  const kind = ticket ? TICKET_KIND[ticket.type] : undefined

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-crew">
            {(['boss', 'inventory', 'accounting', 'facilities', 'customer_service'] as Actor[]).map(a => (
              <Critter key={a} agent={a} size={22} mood={running ? 'busy' : 'idle'} />
            ))}
          </div>
          <div>
            <h1>Campus Customs <span>Ops Floor</span></h1>
            <p>{resolvedCount}/{tickets.length} tickets resolved · shop date {cash?.today ?? '…'}</p>
          </div>
        </div>
        <CashMeter cash={cash} />
        <button className={`btn reset ${confirmReset ? 'confirm' : ''}`} disabled={running !== null} onClick={reset}>
          {confirmReset ? 'Click again to reset' : 'Reset shop'}
        </button>
      </header>

      {offline && <div className="offline">Can't reach the backend at localhost:8000. Start it from backend/ with uvicorn.</div>}

      <main className="floor">
        <aside className="col left">
          <div className="col-title">Ticket board</div>
          <TicketBoard tickets={tickets} selected={selected} onSelect={setSelected} onRun={run} busy={running !== null} />
        </aside>

        <section className="col center">
          {ticket && (
            <div className="ticket-head">
              <div>
                <span className="eyebrow">{kind?.tag ?? ticket.type} · #{ticket.id}</span>
                <h2>{ticket.subject} <small>for {ticket.requester}</small></h2>
                <p className="muted">{ticket.notes?.split('\n')[0]}</p>
              </div>
              <div className={`head-state ${isRunning ? 'running' : isResolved(ticket) ? 'resolved' : ''}`}>
                {isRunning ? 'Crew at work' : isResolved(ticket) ? 'Resolved' : 'Waiting for the crew'}
              </div>
            </div>
          )}
          <CrewMap events={runEvents} active={active} running={isRunning} />
          <div className="feed-wrap">
            <LiveFeed events={runEvents} running={isRunning} active={active} />
          </div>
        </section>

        <aside className="col right">
          <nav className="side-tabs">
            <button className={side === 'approvals' ? 'on' : ''} onClick={() => setSide('approvals')}>
              Approvals {pendingCount > 0 && <span className="badge">{pendingCount}</span>}
            </button>
            <button className={side === 'summary' ? 'on' : ''} onClick={() => setSide('summary')}>Crew summary</button>
            <button className={side === 'drafts' ? 'on' : ''} onClick={() => setSide('drafts')}>
              Drafts {ticket && ticket.drafts.length > 0 && <span className="badge soft">{ticket.drafts.length}</span>}
            </button>
          </nav>
          <div className="side-body">
            {side === 'approvals' && (
              <ApprovalInbox approvals={allApprovals} balance={cash?.checking.balance ?? 0}
                approver={approver} setApprover={setApprover} onApprove={approve} onReject={reject} />
            )}
            {side === 'summary' && <CrewSummary events={runEvents} ticket={ticket} />}
            {side === 'drafts' && <Drafts drafts={ticket?.drafts ?? []} />}
          </div>
          <div className="legend">
            {(['boss', 'inventory', 'accounting', 'facilities', 'customer_service'] as Actor[]).map(a => (
              <span key={a} style={{ ['--c' as string]: AGENTS[a].color }}><i />{AGENTS[a].label}</span>
            ))}
          </div>
        </aside>
      </main>

      {toast && <div className={`toast ${toast.kind}`}>{toast.text}</div>}
    </div>
  )
}
