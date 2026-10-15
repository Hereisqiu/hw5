import { AGENTS, CREW } from '../agents'
import type { Actor, AgentEvent } from '../api'
import { Critter } from './Critter'

// Pentagon positions (percent of the stage), Boss on top.
const POS: Record<string, [number, number]> = {
  boss: [50, 16],
  inventory: [88, 44],
  accounting: [74, 86],
  customer_service: [26, 86],
  facilities: [12, 44],
}

/** The crew as a fully connected graph; edges light up as delegations happen in the current run. */
export function CrewMap({ events, active, running }: { events: AgentEvent[]; active: Actor | null; running: boolean }) {
  const delegations = new Map<string, number>()
  for (const e of events) {
    if (e.event === 'delegate') {
      const key = `${e.agent}>${e.detail.to}`
      delegations.set(key, (delegations.get(key) ?? 0) + 1)
    }
  }
  const involved = new Set(events.filter(e => e.agent !== 'human').map(e => e.agent))
  const pairs: [string, string][] = []
  CREW.forEach((a, i) => CREW.slice(i + 1).forEach(b => pairs.push([a, b])))

  return (
    <div className="crew-stage">
      <svg className="crew-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
        {pairs.map(([a, b]) => (
          <line key={`${a}-${b}`} className="edge-idle"
            x1={POS[a][0]} y1={POS[a][1]} x2={POS[b][0]} y2={POS[b][1]} />
        ))}
        {[...delegations.entries()].map(([key, n]) => {
          const [from, to] = key.split('>')
          return (
            <line key={key} className="edge-live" style={{ strokeWidth: 0.9 + n * 0.4 }}
              x1={POS[from][0]} y1={POS[from][1]} x2={POS[to][0]} y2={POS[to][1]} />
          )
        })}
      </svg>
      {CREW.map(a => {
        const isActive = running && active === a
        const mood = isActive ? 'busy' : involved.has(a) ? 'happy' : 'sleepy'
        return (
          <div key={a} className={`crew-node ${isActive ? 'active' : ''} ${involved.has(a) ? 'involved' : ''}`}
            style={{ left: `${POS[a][0]}%`, top: `${POS[a][1]}%`, ['--c' as string]: AGENTS[a].color }}>
            <Critter agent={a} size={isActive ? 50 : 42} mood={mood} />
            <span className="crew-label">{AGENTS[a].label}</span>
          </div>
        )
      })}
    </div>
  )
}
