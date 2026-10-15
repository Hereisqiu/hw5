# Campus Customs MCP Server

This server holds the shop tools for the Campus Customs operations team. It's built with FastMCP and lives in [`server.py`](server.py). The five agents (Boss, Inventory, Accounting, Facilities, Customer Service) read and change shop data only through these tools.

## Database

The server uses the working copy, `data/campus_customs_new.db`. The original `data/campus_customs.db` stays untouched. To reset:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

The server adds two working tables to the copy if they are missing:
- `approvals`: payments and purchase orders waiting for a human.
- `drafts`: customer messages, which are never sent.

"Today" is always `desk.date_today`, not the computer's clock.

## Tools

| Tool | Reads / writes | Purpose |
|---|---|---|
| `get_shop_date()` | desk | The shop's official today. |
| `list_tickets(status="open")` | tickets | The board. |
| `update_ticket(ticket_id, status, note, author)` | tickets (write) | Set status (`open`, `in_progress`, `waiting_approval`, `resolved`) and add a dated note. |
| `check_stock(sku, size=None)` | inventory | Units on hand per size. |
| `check_bulk_order(sku, size, qty, discount_pct=0)` | inventory, pricing, vendors | Shortfall, restock cost, discounted price and margin, largest discount that still covers cost. |
| `list_vendors()` | vendors, invoices, desk | Specialty, lead time, open invoices, whether each vendor can ship, expected arrival. |
| `get_invoice_status(invoice_id)` | invoices, vendors, desk | One invoice: overdue or not, its vendor, whether that vendor can ship. |
| `list_invoices(status="open")` | invoices, vendors, desk | All invoices with overdue flags. |
| `get_rent_due(lease_id)` | leases, desk, cash_accounts | Rent, due date, days until due, whether cash covers it. |
| `get_cash_position()` | cash_accounts, approvals, payments | Balances, total already queued for approval, payments made. |
| `prepare_payment(kind, ref_id, ticket_id, requested_by, reason, account="checking")` | approvals (write) | Queue an invoice or rent payment for human approval. Amount comes from the database. |
| `prepare_purchase_order(vendor_id, sku, size, qty, ticket_id, requested_by, reason, account="checking")` | approvals (write) | Queue a restock order for human approval. Flags vendors blocked by an open invoice. |
| `list_approvals(status="pending")` | approvals | What is waiting for a human. |
| `save_customer_draft(ticket_id, recipient, subject, body, author)` | drafts (write) | Save a customer message as a draft. |
| `list_drafts(ticket_id=None)` | drafts | Drafts on the board. |
| `approve_payment(approval_id, approved_by)` | approvals, cash_accounts, payments, invoices, leases (write) | **Human only.** Pay a queued item. |
| `reject_payment(approval_id, rejected_by, reason)` | approvals (write) | **Human only.** Reject a queued item. |

### Payment safeguards
- Agents can only *prepare* payments. The backend hides `approve_payment` and `reject_payment` from every agent, and those tools refuse an agent name as the approver.
- A payment is refused if it would make the balance negative.
- A purchase order can't be approved while its vendor has an open invoice.
- On approval, the server subtracts the cash, records the payment with `approved_by`, and marks the invoice paid or moves the lease's `next_due` forward a month.

## Running

```bash
python mcp_server/server.py          # stdio (what .mcp.json and the backend use)
python mcp_server/server.py --http   # http://127.0.0.1:8002/mcp
```
