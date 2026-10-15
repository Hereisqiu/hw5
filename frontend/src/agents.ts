import type { Actor } from './api'

export interface AgentMeta {
  name: Actor
  label: string
  role: string
  color: string
}

export const AGENTS: Record<Actor, AgentMeta> = {
  boss: { name: 'boss', label: 'Boss', role: 'Reads tickets, delegates, makes the final call', color: '#ff4fa3' },
  inventory: { name: 'inventory', label: 'Inventory', role: 'Stock, shortfalls, restock vendors', color: '#4fe3b0' },
  accounting: { name: 'accounting', label: 'Accounting', role: 'Cash, invoices, margins, approvals', color: '#ffd166' },
  facilities: { name: 'facilities', label: 'Facilities', role: 'Leases and rent', color: '#5cc8ff' },
  customer_service: {
    name: 'customer_service', label: 'Customer Service', role: 'Drafts messages (never sends)', color: '#b78cff',
  },
  human: { name: 'human', label: 'You', role: 'Human approver', color: '#f3f0f4' },
}

export const CREW: Actor[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TICKET_KIND: Record<string, { tag: string; glyph: string }> = {
  customer_order: { tag: 'Order', glyph: '◆' },
  rent_notice: { tag: 'Rent', glyph: '⌂' },
  price_override: { tag: 'Deal', glyph: '%' },
}
