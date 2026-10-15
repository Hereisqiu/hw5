"""Campus Customs MCP server: shop tools shared by every agent.

Reads and writes the working copy data/campus_customs_new.db. The original
data/campus_customs.db is never touched, so it can be copied back to reset.

Money never moves without a human: agents can only *prepare* payments and
purchase orders (rows in `approvals`). `approve_payment` / `reject_payment`
are for the human approver; the backend hides them from every agent.

Run (stdio):  python mcp_server/server.py
Run (HTTP):   python mcp_server/server.py --http
HTTP URL:     http://127.0.0.1:8002/mcp
"""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "waiting_approval", "resolved")

# Working tables the agents need on top of the original schema. They only ever
# exist in the working copy; resetting from campus_customs.db removes them.
WORK_TABLES = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,              -- invoice | rent | purchase_order
    ref_id INTEGER,                  -- invoices.id or leases.id (NULL for purchase orders)
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,            -- pending | paid | rejected | refused
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
"""

mcp = FastMCP("campus-customs")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Open the working database; commit on success, roll back on error, always close."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(WORK_TABLES)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _add_month(day: str) -> str:
    d = date.fromisoformat(day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for dd in (d.day, 30, 29, 28):
        try:
            return date(year, month, dd).isoformat()
        except ValueError:
            continue
    raise ValueError(day)


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)
    )
    return [dict(r) for r in rows]


def _cash_summary(conn: sqlite3.Connection, account: str) -> dict:
    acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    pending = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n FROM approvals "
        "WHERE account = ? AND status = 'pending'",
        (account,),
    ).fetchone()
    balance = acct["balance"] if acct else None
    return {
        "account": account,
        "balance": balance,
        "pending_approvals": pending["n"],
        "pending_total": pending["total"],
        "balance_if_all_pending_paid": None if balance is None else round(balance - pending["total"], 2),
    }


@mcp.tool
def get_invoice_status(invoice_id: int) -> dict:
    """Look up a vendor invoice with its vendor and whether it is overdue.

    Reads invoices, vendors, and desk. An open invoice blocks that vendor from
    shipping new product, so this also reports whether the vendor can ship.
    """
    with _connect() as conn:
        row = conn.execute(
            """SELECT i.id, i.amount, i.due_date, i.status, i.description,
                      v.id AS vendor_id, v.name AS vendor_name, v.specialty, v.lead_days
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"error": f"Invoice {invoice_id} not found."}
        today = _today(conn)

    days_past_due = _days_between(row["due_date"], today)
    is_open = row["status"] == "open"
    return {
        "invoice_id": row["id"],
        "amount": row["amount"],
        "due_date": row["due_date"],
        "status": row["status"],
        "description": row["description"],
        "today": today,
        "overdue": is_open and days_past_due > 0,
        "days_past_due": max(days_past_due, 0),
        "vendor": {
            "id": row["vendor_id"],
            "name": row["vendor_name"],
            "specialty": row["specialty"],
            "lead_days": row["lead_days"],
        },
        "vendor_can_ship": not is_open,
    }


@mcp.tool
def get_rent_due(lease_id: int) -> dict:
    """Look up a lease's rent, due date, and whether checking can cover it.

    Reads leases, desk, and cash_accounts. Does not pay anything; payments
    need human approval.
    """
    with _connect() as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            return {"error": f"Lease {lease_id} not found."}
        today = _today(conn)
        accounts = [dict(r) for r in conn.execute("SELECT name, balance, date FROM cash_accounts")]

    days_until_due = _days_between(today, lease["next_due"])
    rent = lease["monthly_rent"]
    return {
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": rent,
        "next_due": lease["next_due"],
        "notes": lease["notes"],
        "today": today,
        "days_until_due": days_until_due,
        "overdue": days_until_due < 0,
        "cash_accounts": [
            {**a, "can_cover_rent": a["balance"] >= rent, "balance_after_rent": a["balance"] - rent}
            for a in accounts
        ],
    }


@mcp.tool
def check_bulk_order(sku: str, size: str, qty: int, discount_pct: float = 0.0) -> dict:
    """Check stock and margin for an order of one SKU and size, optionally discounted.

    Reads inventory, pricing, and vendors. Reports units on hand, the shortfall,
    restock cost at unit cost, which vendors could restock, and the per-unit and
    total margin at the requested discount off list price.
    """
    if qty <= 0:
        return {"error": "qty must be positive."}
    if not 0 <= discount_pct < 100:
        return {"error": "discount_pct must be between 0 and 100."}

    with _connect() as conn:
        item = conn.execute(
            "SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if item is None:
            sizes = [r["size"] for r in conn.execute("SELECT size FROM inventory WHERE sku = ?", (sku,))]
            if sizes:
                return {"error": f"{sku} has no size {size}. Sizes: {sizes}."}
            return {"error": f"SKU {sku} not found."}
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        vendors = [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY id")]

    on_hand = item["qty"]
    shortfall = max(qty - on_hand, 0)
    unit_cost = price["unit_cost"]
    list_price = price["list_price"]
    unit_price = round(list_price * (1 - discount_pct / 100), 2)
    unit_margin = round(unit_price - unit_cost, 2)
    return {
        "sku": sku,
        "name": item["name"],
        "size": size,
        "location": item["location"],
        "requested_qty": qty,
        "on_hand": on_hand,
        "can_fill_from_stock": shortfall == 0,
        "shortfall": shortfall,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "discount_pct": discount_pct,
        "discounted_unit_price": unit_price,
        "unit_margin": unit_margin,
        "margin_pct": round(unit_margin / unit_price * 100, 1) if unit_price else None,
        "order_total": round(unit_price * qty, 2),
        "order_margin": round(unit_margin * qty, 2),
        "below_cost": unit_price < unit_cost,
        "max_discount_pct_at_cost": round((1 - unit_cost / list_price) * 100, 1),
        "restock_cost": round(shortfall * unit_cost, 2),
        "vendors": vendors,
    }


# ---------------------------------------------------------------- board / desk


@mcp.tool
def get_shop_date() -> dict:
    """Return the shop's official "today" (desk.date_today). Use it for every due/overdue check."""
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    return dict(row)


@mcp.tool
def list_tickets(status: str | None = "open") -> list[dict]:
    """List tickets on the board (default: open ones). Pass status=None for all tickets.

    Reads tickets. Each ticket links to inventory (sku/size/qty), leases (lease_id)
    or invoices (invoice_id).
    """
    with _connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,))
        else:
            rows = conn.execute("SELECT * FROM tickets ORDER BY id")
        return [dict(r) for r in rows]


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str, author: str) -> dict:
    """Set a ticket's status and append a dated note (open, in_progress, waiting_approval, resolved).

    Writes tickets. Use waiting_approval when a payment or purchase order is
    waiting on a human, and resolved only when nothing is left to do.
    """
    if status not in TICKET_STATUSES:
        return {"error": f"status must be one of {list(TICKET_STATUSES)}."}
    if not note.strip():
        return {"error": "note is required."}
    with _connect() as conn:
        ticket = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"error": f"Ticket {ticket_id} not found."}
        line = f"[{_today(conn)} {author}] {note.strip()}"
        notes = f"{ticket['notes']}\n{line}" if ticket["notes"] else line
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
        return dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())


# ---------------------------------------------------------------- inventory / vendors


@mcp.tool
def check_stock(sku: str, size: str | None = None) -> list[dict] | dict:
    """Units on hand for a SKU, for one size or every size. Reads inventory."""
    with _connect() as conn:
        if size:
            rows = conn.execute("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)).fetchall()
    if not rows:
        return {"error": f"No inventory for sku={sku}" + (f", size={size}" if size else "") + "."}
    return [dict(r) for r in rows]


@mcp.tool
def list_vendors() -> list[dict]:
    """Every vendor with specialty, lead time, open invoices, and whether they can ship now.

    Reads vendors, invoices and desk. A vendor with any open invoice cannot ship new
    product; expected_arrival_if_ordered_today is today + lead_days.
    """
    with _connect() as conn:
        today = _today(conn)
        out = []
        for v in conn.execute("SELECT * FROM vendors ORDER BY id").fetchall():
            open_inv = _open_invoices(conn, v["id"])
            out.append({
                **dict(v),
                "open_invoices": open_inv,
                "can_ship": not open_inv,
                "expected_arrival_if_ordered_today": (
                    date.fromisoformat(today) + timedelta(days=v["lead_days"])
                ).isoformat(),
            })
    return out


# ---------------------------------------------------------------- money


@mcp.tool
def list_invoices(status: str | None = "open") -> list[dict]:
    """List vendor invoices (default: open) with vendor name and overdue flag. Reads invoices, vendors, desk."""
    with _connect() as conn:
        today = _today(conn)
        sql = ("SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id"
               + (" WHERE i.status = ?" if status else "") + " ORDER BY i.due_date")
        rows = conn.execute(sql, (status,) if status else ()).fetchall()
    return [
        {**dict(r), "overdue": r["status"] == "open" and r["due_date"] < today,
         "days_past_due": max(_days_between(r["due_date"], today), 0)}
        for r in rows
    ]


@mcp.tool
def get_cash_position() -> dict:
    """Cash balances, money already promised to pending approvals, and payments made so far.

    Reads cash_accounts, approvals and payments. Cash only goes out; no revenue is modeled.
    """
    with _connect() as conn:
        accounts = [r["name"] for r in conn.execute("SELECT name FROM cash_accounts")]
        payments = [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]
        return {
            "today": _today(conn),
            "accounts": [_cash_summary(conn, a) for a in accounts],
            "payments": payments,
        }


@mcp.tool
def prepare_payment(
    kind: Literal["invoice", "rent"],
    ref_id: int,
    ticket_id: int,
    requested_by: str,
    reason: str,
    account: str = "checking",
) -> dict:
    """Queue an invoice or rent payment for HUMAN approval. Does not move any money.

    kind="invoice": ref_id is invoices.id. kind="rent": ref_id is leases.id.
    The amount is taken from the database, never from the caller. Refused if the
    account could not cover it even on its own. Writes approvals.
    """
    with _connect() as conn:
        if kind == "invoice":
            row = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"error": f"Invoice {ref_id} not found."}
            if row["status"] != "open":
                return {"error": f"Invoice {ref_id} is already {row['status']}."}
            amount = row["amount"]
        else:
            row = conn.execute("SELECT monthly_rent FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"error": f"Lease {ref_id} not found."}
            amount = row["monthly_rent"]

        dup = conn.execute(
            "SELECT id FROM approvals WHERE kind = ? AND ref_id = ? AND status = 'pending'", (kind, ref_id)
        ).fetchone()
        if dup:
            return {"error": f"A pending approval already exists for this {kind} (approval {dup['id']}).",
                    "approval_id": dup["id"]}

        cash = _cash_summary(conn, account)
        if cash["balance"] is None:
            return {"error": f"Cash account {account!r} not found."}
        if amount > cash["balance"]:
            return {"error": f"Refused: {account} balance ${cash['balance']:.2f} cannot cover ${amount:.2f}.",
                    "cash": cash}

        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, amount, account, reason, requested_by, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (ticket_id, kind, ref_id, amount, account, reason, requested_by, _now()),
        )
        approval = dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (cur.lastrowid,)).fetchone())
        cash = _cash_summary(conn, account)
    return {
        "approval": approval,
        "cash": cash,
        "warning": "Pending approvals exceed the balance; a human must choose which to pay."
        if cash["balance_if_all_pending_paid"] < 0 else None,
    }


@mcp.tool
def prepare_purchase_order(
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    ticket_id: int,
    requested_by: str,
    reason: str,
    account: str = "checking",
) -> dict:
    """Queue a restock purchase order for HUMAN approval. Does not move money or stock.

    Cost = qty x pricing.unit_cost. If the vendor still has an open invoice it cannot
    ship, so the order is flagged as blocked and approval will be refused until that
    invoice is paid. Reads inventory, pricing, vendors, invoices; writes approvals.
    """
    if qty <= 0:
        return {"error": "qty must be positive."}
    with _connect() as conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"error": f"Vendor {vendor_id} not found."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"error": f"No inventory row for {sku} size {size}."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        amount = round(qty * price["unit_cost"], 2)

        cash = _cash_summary(conn, account)
        if cash["balance"] is None:
            return {"error": f"Cash account {account!r} not found."}
        if amount > cash["balance"]:
            return {"error": f"Refused: {account} balance ${cash['balance']:.2f} cannot cover ${amount:.2f}.",
                    "cash": cash}

        blocked_by = _open_invoices(conn, vendor_id)
        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, vendor_id, sku, size, qty, amount, account, reason, "
            "requested_by, status, created_at) VALUES (?, 'purchase_order', ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (ticket_id, vendor_id, sku, size, qty, amount, account, reason, requested_by, _now()),
        )
        approval = dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (cur.lastrowid,)).fetchone())
        cash = _cash_summary(conn, account)
    return {
        "approval": approval,
        "vendor": dict(vendor),
        "vendor_blocked_by_open_invoices": blocked_by,
        "cash": cash,
        "warning": "; ".join(w for w in [
            f"{vendor['name']} has open invoice(s) {[i['id'] for i in blocked_by]}; pay them first." if blocked_by else "",
            "Pending approvals exceed the balance; a human must choose which to pay."
            if cash["balance_if_all_pending_paid"] < 0 else "",
        ] if w) or None,
    }


@mcp.tool
def list_approvals(status: str | None = "pending") -> list[dict]:
    """Payments and purchase orders queued for human approval (default: pending). Reads approvals."""
    with _connect() as conn:
        if status:
            rows = conn.execute("SELECT * FROM approvals WHERE status = ? ORDER BY id", (status,))
        else:
            rows = conn.execute("SELECT * FROM approvals ORDER BY id")
        return [dict(r) for r in rows]


@mcp.tool
def approve_payment(approval_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve and execute a queued payment or purchase order.

    Refuses if the cash account would go negative or the vendor still has an open
    invoice. On success: debits cash_accounts, inserts into payments, marks the
    invoice paid / moves the lease's next_due forward a month, and marks the
    approval paid.
    """
    approver = approved_by.strip()
    if not approver or approver.lower() in AGENT_NAMES:
        return {"error": "approved_by must be the name of the human approver."}
    with _connect() as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"error": f"Approval {approval_id} not found."}
        if a["status"] != "pending":
            return {"error": f"Approval {approval_id} is already {a['status']}."}
        today = _today(conn)

        if a["kind"] == "purchase_order":
            blocked = _open_invoices(conn, a["vendor_id"])
            if blocked:
                return {"error": f"Vendor still has open invoice(s) {[i['id'] for i in blocked]}; "
                                 "pay them before approving this purchase order. Approval left pending."}
        if a["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (a["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"error": f"Invoice {a['ref_id']} is no longer open."}

        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (a["account"],)).fetchone()
        if acct is None or acct["balance"] < a["amount"]:
            note = f"Refused: {a['account']} balance ${acct['balance'] if acct else 0:.2f} < ${a['amount']:.2f}."
            conn.execute(
                "UPDATE approvals SET status = 'refused', decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
                (approver, _now(), note, approval_id),
            )
            return {"error": note}

        new_balance = round(acct["balance"] - a["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today, a["account"]))
        ref_id = a["ref_id"] if a["kind"] != "purchase_order" else a["id"]
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (a["kind"], ref_id, a["amount"], a["account"], today, approver),
        )
        note = None
        if a["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
            note = f"Invoice {a['ref_id']} marked paid."
        elif a["kind"] == "rent":
            due = conn.execute("SELECT next_due FROM leases WHERE id = ?", (a["ref_id"],)).fetchone()["next_due"]
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_month(due), a["ref_id"]))
            note = f"Lease {a['ref_id']} next_due moved from {due} to {_add_month(due)}."
        else:
            lead = conn.execute("SELECT lead_days FROM vendors WHERE id = ?", (a["vendor_id"],)).fetchone()["lead_days"]
            arrival = (date.fromisoformat(today) + timedelta(days=lead)).isoformat()
            note = f"PO for {a['qty']} x {a['sku']} {a['size']} placed; expected arrival {arrival}."
        conn.execute(
            "UPDATE approvals SET status = 'paid', decided_by = ?, decided_at = ?, decision_note = ?, payment_id = ? "
            "WHERE id = ?",
            (approver, _now(), note, cur.lastrowid, approval_id),
        )
        return {
            "approval": dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()),
            "payment": dict(conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone()),
            "new_balance": new_balance,
            "note": note,
        }


@mcp.tool
def reject_payment(approval_id: int, rejected_by: str, reason: str) -> dict:
    """HUMAN ONLY. Reject a queued payment or purchase order. No money moves. Writes approvals."""
    who = rejected_by.strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"error": "rejected_by must be the name of the human approver."}
    with _connect() as conn:
        a = conn.execute("SELECT status FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"error": f"Approval {approval_id} not found."}
        if a["status"] != "pending":
            return {"error": f"Approval {approval_id} is already {a['status']}."}
        conn.execute(
            "UPDATE approvals SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
            (who, _now(), reason, approval_id),
        )
        return dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone())


# ---------------------------------------------------------------- customer drafts


@mcp.tool
def save_customer_draft(ticket_id: int, recipient: str, subject: str, body: str, author: str) -> dict:
    """Save a customer message as a DRAFT on the board. Nothing is ever sent. Writes drafts."""
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"error": f"Ticket {ticket_id} not found."}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, recipient, subject, body, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, recipient, subject, body, author, _now()),
        )
        return dict(conn.execute("SELECT * FROM drafts WHERE id = ?", (cur.lastrowid,)).fetchone())


@mcp.tool
def list_drafts(ticket_id: int | None = None) -> list[dict]:
    """Customer message drafts on the board, optionally for one ticket. Reads drafts."""
    with _connect() as conn:
        if ticket_id is None:
            rows = conn.execute("SELECT * FROM drafts ORDER BY id")
        else:
            rows = conn.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))
        return [dict(r) for r in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=args.port, show_banner=False)
    else:
        mcp.run(show_banner=False)
