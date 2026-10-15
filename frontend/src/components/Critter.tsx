import type { CSSProperties } from 'react'
import { AGENTS } from '../agents'
import type { Actor } from '../api'

/** A little CSS-only creature for each agent. Each has its own colour and accessory. */
export function Critter({ agent, size = 44, mood = 'idle' }: {
  agent: Actor
  size?: number
  mood?: 'idle' | 'busy' | 'happy' | 'sleepy'
}) {
  const style = { '--c': AGENTS[agent].color, '--s': `${size}px` } as CSSProperties
  return (
    <span className={`critter critter-${agent} mood-${mood}`} style={style} title={AGENTS[agent].label}>
      <span className="critter-gear" />
      <span className="critter-body">
        <span className="critter-eye left" />
        <span className="critter-eye right" />
        <span className="critter-mouth" />
        <span className="critter-blush left" />
        <span className="critter-blush right" />
      </span>
    </span>
  )
}
