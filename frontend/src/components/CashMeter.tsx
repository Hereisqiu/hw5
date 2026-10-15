import { useEffect, useRef, useState } from 'react'
import { money, type Cash } from '../api'

const START = 3400 // the shop's opening balance in data/campus_customs.db

/** Counts smoothly from the old value to the new one. */
function useCountUp(target: number) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    const start = performance.now()
    const begin = from.current
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min((now - start) / 900, 1)
      const v = begin + (target - begin) * (1 - Math.pow(1 - p, 3))
      setShown(v)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target])
  return shown
}

export function CashMeter({ cash }: { cash: Cash | null }) {
  const balance = cash?.checking.balance ?? 0
  const pending = cash?.checking.pending_total ?? 0
  const shown = useCountUp(balance)
  const [flash, setFlash] = useState(false)
  const prev = useRef<number | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (prev.current !== null && prev.current !== balance) {
      setFlash(true)
      const t = setTimeout(() => setFlash(false), 1200)
      return () => clearTimeout(t)
    }
    prev.current = balance
  }, [balance])
  useEffect(() => { prev.current = balance }, [balance])

  const max = Math.max(START, balance)
  const after = balance - pending
  const short = after < 0
  return (
    <div className={`cash ${flash ? 'flash' : ''}`} onClick={() => setOpen(o => !o)}>
      <div className="cash-label">Checking <span>{cash ? `as of ${cash.today}` : ''}</span></div>
      <div className="cash-amount">{cash ? money(shown) : '—'}</div>
      <div className="cash-bar" title="Pink = cash left after every pending approval, striped = queued for approval">
        <span className="cash-fill" style={{ width: `${(Math.max(after, 0) / max) * 100}%` }} />
        <span className="cash-pending" style={{ width: `${(Math.min(pending, balance) / max) * 100}%` }} />
      </div>
      <div className={`cash-sub ${short ? 'short' : ''}`}>
        {pending > 0
          ? <>{money(pending)} queued · {short ? `short by ${money(-after)}` : `${money(after)} after approvals`}</>
          : 'Nothing waiting for approval'}
      </div>
      {open && cash && (
        <div className="ledger" onClick={e => e.stopPropagation()}>
          <div className="ledger-title">Payments out</div>
          {cash.payments.length === 0 && <p className="muted">No payments yet. Cash only goes out in this shop.</p>}
          {cash.payments.map(p => (
            <div key={p.id} className="ledger-row">
              <span>{p.kind} #{p.ref_id}</span>
              <span className="neg">−{money(p.amount)}</span>
              <span className="muted">{p.approved_by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
