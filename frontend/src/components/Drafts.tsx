import { AGENTS } from '../agents'
import type { Draft } from '../api'

/** Customer messages stay on the board as drafts; nothing is ever sent. */
export function Drafts({ drafts }: { drafts: Draft[] }) {
  if (drafts.length === 0) return <p className="muted">No customer drafts for this ticket.</p>
  return (
    <div className="drafts">
      {drafts.map(d => (
        <div key={d.id} className="postcard">
          <div className="postcard-stamp">Draft · not sent</div>
          <div className="postcard-to">To: <b>{d.recipient}</b></div>
          <div className="postcard-subject">{d.subject}</div>
          <p className="postcard-body">{d.body}</p>
          <div className="postcard-from">— drafted by {AGENTS[d.author as keyof typeof AGENTS]?.label ?? d.author}</div>
        </div>
      ))}
    </div>
  )
}
