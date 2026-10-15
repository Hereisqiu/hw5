import { useEffect, useRef, useState } from 'react'
import { AGENTS } from '../agents'
import type { Actor, AgentEvent } from '../api'
import { Critter } from './Critter'

const HIDDEN_TOOLS = new Set(['final_result'])

function pretty(value: unknown): string {
  if (typeof value !== 'string') return JSON.stringify(value, null, 2)
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

function argsPreview(args: Record<string, unknown> | undefined): string {
  if (!args) return ''
  return Object.entries(args)
    .filter(([k]) => !['reason', 'note', 'body', 'requested_by', 'author'].includes(k))
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}

function ToolChip({ call, result }: { call: AgentEvent; result?: AgentEvent }) {
  const [open, setOpen] = useState(false)
  const failed = typeof result?.detail.result === 'string' && result.detail.result.includes('"error"')
  return (
    <div className={`tool-chip ${open ? 'open' : ''} ${failed ? 'failed' : ''}`}>
      <button onClick={() => setOpen(o => !o)}>
        <span className="tool-icon">⚙</span>
        <span className="tool-name">{call.detail.tool}</span>
        <span className="tool-args">{argsPreview(call.detail.args)}</span>
        <span className="tool-state">{result ? (failed ? 'refused' : 'done') : '…'}</span>
      </button>
      {open && (
        <div className="tool-body">
          <div className="tool-section">args</div>
          <pre>{pretty(call.detail.args)}</pre>
          {result && <><div className="tool-section">result</div><pre>{pretty(result.detail.result)}</pre></>}
        </div>
      )}
    </div>
  )
}

function Report({ e }: { e: AgentEvent }) {
  const out = e.detail.output ?? {}
  const facts: string[] = out.facts ?? []
  const issues: string[] = out.open_issues ?? out.blockers ?? []
  return (
    <div className="report">
      <div className="report-title">{e.agent === 'boss' && e.depth === 0 ? 'Final call' : 'Report back'}</div>
      <p>{out.decision ?? out.summary}</p>
      {facts.length > 0 && <ul className="facts-list">{facts.map((f, i) => <li key={i}>{f}</li>)}</ul>}
      {out.recommendation && <p className="rec"><b>Next:</b> {out.recommendation}</p>}
      {issues.length > 0 && <ul className="issues-list">{issues.map((f, i) => <li key={i}>{f}</li>)}</ul>}
    </div>
  )
}

/** Chat-style stream of what each agent says and does for the selected ticket. */
export function LiveFeed({ events, running, active }: { events: AgentEvent[]; running: boolean; active: Actor | null }) {
  const end = useRef<HTMLDivElement>(null)
  const [follow, setFollow] = useState(true)
  useEffect(() => {
    if (follow) end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [events.length, follow])

  const results = new Map<number, AgentEvent>()
  const pending: AgentEvent[] = []
  for (const e of events) {
    if (e.event === 'tool_call') pending.push(e)
    if (e.event === 'tool_result') {
      const i = pending.findIndex(c => c.agent === e.agent && c.run_id === e.run_id && c.detail.tool === e.detail.tool
        && c.chain.join() === e.chain.join())
      if (i >= 0) results.set(pending.splice(i, 1)[0].seq, e)
    }
  }

  const items = events.filter(e =>
    !['tool_result', 'reset'].includes(e.event) &&
    !(e.event === 'tool_call' && (HIDDEN_TOOLS.has(e.detail.tool) || e.detail.tool === 'delegate')))

  if (items.length === 0) {
    return (
      <div className="feed-empty">
        <Critter agent="boss" size={64} mood="sleepy" />
        <p>The crew is waiting. Press <b>Send the crew</b> to start this ticket.</p>
      </div>
    )
  }

  return (
    <div className="feed" onScroll={ev => {
      const el = ev.currentTarget
      setFollow(el.scrollHeight - el.scrollTop - el.clientHeight < 80)
    }}>
      {items.map(e => {
        const meta = AGENTS[e.agent]
        const side = e.agent === 'human' ? 'right' : 'left'
        const indent = { marginLeft: `${Math.min(e.depth, 3) * 22}px` }
        if (e.event === 'delegate') {
          const to = e.detail.to as Actor
          return (
            <div key={e.seq} className="handoff" style={indent}>
              <Critter agent={e.agent} size={22} />
              <span className="handoff-arrow" style={{ ['--a' as string]: meta.color, ['--b' as string]: AGENTS[to].color }}>
                {meta.label} <span>→</span> {AGENTS[to].label}
              </span>
              <Critter agent={to} size={22} />
              <p className="handoff-task">{e.detail.task}</p>
            </div>
          )
        }
        if (e.event === 'start') {
          if (e.depth > 0) return null
          return <div key={e.seq} className="system-line">Boss picked up the ticket · {new Date(e.timestamp).toLocaleTimeString()}</div>
        }
        if (e.event === 'tool_call') {
          return (
            <div key={e.seq} className="tool-row" style={{ ...indent, ['--c' as string]: meta.color }}>
              <ToolChip call={e} result={results.get(e.seq)} />
            </div>
          )
        }
        return (
          <div key={e.seq} className={`bubble-row ${side}`} style={side === 'left' ? indent : undefined}>
            {side === 'left' && <Critter agent={e.agent} size={34} />}
            <div className={`bubble ${e.event}`} style={{ ['--c' as string]: meta.color }}>
              <div className="bubble-who">{meta.label}<span>{new Date(e.timestamp).toLocaleTimeString()}</span></div>
              {e.event === 'finish' ? <Report e={e} /> : <p>{e.message}</p>}
            </div>
            {side === 'right' && <Critter agent="human" size={34} mood="happy" />}
          </div>
        )
      })}
      {running && active && (
        <div className="bubble-row left typing">
          <Critter agent={active} size={34} mood="busy" />
          <div className="bubble" style={{ ['--c' as string]: AGENTS[active].color }}>
            <div className="dots"><i /><i /><i /></div>
            <span className="typing-label">{AGENTS[active].label} is working…</span>
          </div>
        </div>
      )}
      <div ref={end} />
    </div>
  )
}
