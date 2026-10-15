# Campus Customs Multi-Agent Operations — Harness

This is the agent team's guide to the shop's data, tools, and rules. Each later problem adds to it.

## Database

- **Original database:** `data/campus_customs.db`. Never changed. Copy it over the working database to reset.
- **Working database:** `data/campus_customs_new.db`. The MCP server and backend read and write this copy.

Reset command:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

## Tables

### `desk`
The shop's clock. It has one row.

| Field | Purpose |
|---|---|
| `date_today` | The shop's "today" (`2026-08-31`). Agents use this date for every overdue or due-soon check, not the computer's clock. |
| `notes` | Free-text notes for the desk. Currently empty. |

### `tickets`
The board of open work items. The Boss reads each ticket and assigns it to an agent.

| Field | Purpose |
|---|---|
| `id` | Ticket number shown on the dashboard. |
| `type` | What kind of work it is (`customer_order`, `rent_notice`, `price_override`). The Boss uses this to pick an agent. |
| `requester` | Who asked: a customer, the landlord, or a student org. Customer Service writes drafts to this person. |
| `subject` | Short headline for the board. |
| `sku` | Product involved, if any. Links to `inventory` and `pricing`. |
| `size` | Size requested. Combined with `sku`, it identifies one `inventory` row. |
| `qty` | Units requested. Inventory compares this with stock on hand. |
| `lease_id` | Lease involved, if any. Links to `leases`. Used by Facilities. |
| `invoice_id` | Vendor invoice involved, if any. Links to `invoices`. Used by Accounting. |
| `status` | `open` until the team resolves the ticket. |
| `notes` | Details from the requester. |
| `created_at` | When the ticket arrived (ISO timestamp). |

### `inventory`
Stock on hand. The primary key is (`sku`, `size`).

| Field | Purpose |
|---|---|
| `sku` | Product code. |
| `name` | Product name, used in customer messages. |
| `size` | S / M / L / XL, or OS (one size). |
| `qty` | Units on hand. Inventory checks this for shortfalls. |
| `location` | Aisle where the product is shelved, used for pick instructions. |

### `pricing`
Cost and price for each SKU. Accounting uses it to check margins.

| Field | Purpose |
|---|---|
| `sku` | Product code. Links to `inventory`. |
| `unit_cost` | What the shop pays a vendor per unit. Used to cost purchase orders and to set the lowest acceptable discounted price. |
| `list_price` | Normal selling price. Discounts are measured against it. |

### `vendors`
Suppliers that can restock the shop.

| Field | Purpose |
|---|---|
| `id` | Vendor ID. Links to `invoices`. |
| `name` | Vendor name. |
| `specialty` | What the vendor supplies: apparel, mugs and small goods, or local courier. Inventory uses it to choose a restock vendor. |
| `lead_days` | Days from order to delivery. Used to estimate when stock arrives. |

### `leases`
The shop's rented space. Owned by Facilities.

| Field | Purpose |
|---|---|
| `id` | Lease ID. Links from `tickets.lease_id`. |
| `space_name` | Name of the space (Chapel Street shop). |
| `landlord` | Who is paid rent. |
| `monthly_rent` | Rent amount. |
| `next_due` | Next rent due date. Compared with `desk.date_today`. When rent is paid, this moves forward a month. |
| `notes` | Lease notes. |

### `cash_accounts`
The money the shop can spend. No money comes in during this homework.

| Field | Purpose |
|---|---|
| `name` | Account name (`checking`). |
| `balance` | Current balance. The pay tool must refuse any payment that would push it below 0. |
| `date` | Date of the last balance update. |

### `payments`
Record of money paid out. Empty at the start. Each human-approved payment adds a row.

| Field | Purpose |
|---|---|
| `id` | Payment ID. |
| `kind` | What was paid, e.g. `invoice`, `rent`, or `purchase_order`. |
| `ref_id` | ID of the invoice or lease that was paid. |
| `amount` | Amount paid. |
| `account` | Cash account it came from. Links to `cash_accounts.name`. |
| `paid_at` | Payment date. |
| `approved_by` | The human who approved it. Required for every payment. |

### `invoices`
Bills from vendors.

| Field | Purpose |
|---|---|
| `id` | Invoice ID. Links from `tickets.invoice_id`. |
| `vendor_id` | Which vendor sent the bill. Links to `vendors`. |
| `amount` | Amount owed. |
| `due_date` | Due date. It is overdue if earlier than `desk.date_today`. |
| `status` | `open` means unpaid; `paid` after payment. A vendor with an `open` invoice will not ship new product. |
| `description` | What the bill was for. |

## Starting data

- Today is **2026-08-31**.
- Checking balance is **$3,400**.
- No payments have been made.

## Open tickets and how they connect

### Ticket 101: customer order
Tauhid Zaman wants 1 × `CC-TEE-WHITE` (Classic Bulldog Tee), size S.

- **Inventory:** size S has 0 units in stock, so the order can't be filled from the shelf.
- **Invoice:** the ticket links to invoice **501** from Bulldog Print Co (vendor 1, apparel reprint, 5-day lead time).
  - It is $840 for a "Rush reprint CC-TEE-WHITE S".
  - It was due 2026-08-28, so it is **overdue** and still `open`.
- **Blocked:** Bulldog Print Co won't ship the reprint until invoice 501 is paid.
- **Steps:**
  1. Accounting prepares the $840 payment for human approval.
  2. After it is paid, stock arrives about 5 days later.
  3. Customer Service drafts an update for the customer.

### Ticket 102: rent notice
Elm City Properties gave notice that rent is due on lease **1** (Chapel Street shop).

- **Amount and date:** $2,400, due 2026-09-02. That is 2 days away, not overdue yet.
- **Steps:**
  1. Facilities confirms the lease details.
  2. Accounting prepares the rent payment for human approval.
  3. After payment, `leases.next_due` moves to 2026-10-02.

### Ticket 103: price override
The Yale AI Club wants 20 × `CC-HOOD-NAVY`, size M, and is asking for a bulk discount.

- **Inventory:** 8 in stock, so the shortfall is **12**.
- **Restock:**
  - The apparel vendor is Bulldog Print Co, which is blocked by invoice 501.
  - Restocking 12 units costs about 12 × $22 = $264.
  - The vendor's lead time is 5 days.
- **Margin:** unit cost is $22 and list price is $58.
  - Accounting must keep any discounted price above cost.
  - The Boss makes the final call on the discount.
  - Customer Service drafts the reply.

### How the tickets affect each other
All three tickets draw on the same $3,400.

- Invoice 501 ($840) plus rent ($2,400) comes to $3,240. That leaves **$160**.
- $160 isn't enough for the roughly $264 hoodie restock. The agents need to recognize this and ask a human which payments come first.
- Invoice 501 blocks both the tee restock (101) and the hoodie restock (103).

## MCP server tools

The server is `mcp_server/server.py`, built with FastMCP and pointed at `data/campus_customs_new.db`. Every agent gets its shop data and makes every change through these tools. There is no other shop-tools layer.

- Tools return database values plus simple arithmetic on them (days overdue, shortfall, margin).
- "Today" always comes from `desk.date_today`.

### Problem 3 tools

### `get_invoice_status(invoice_id)`
- **Reads:** `invoices`, `vendors`, `desk`
- **Supports:** ticket **101**
- **How it helps:** It shows that invoice 501, Bulldog Print Co's $840 bill for the size S tee reprint, is 3 days overdue and still open, so Accounting knows this bill must be paid before the vendor will ship Tauhid's tee, which arrives 5 days after payment.

### `get_rent_due(lease_id)`
- **Reads:** `leases`, `desk`, `cash_accounts`
- **Supports:** ticket **102**
- **How it helps:** It confirms the Chapel Street shop's $2,400 rent to Elm City Properties is due 2026-09-02 (2 days away, not yet late) and that the $3,400 in checking covers it, leaving $1,000, so Facilities can pass Accounting the exact rent payment to request approval for.

### `check_bulk_order(sku, size, qty, discount_pct=0)`
- **Reads:** `inventory`, `pricing`, `vendors`
- **Supports:** ticket **103**
- **How it helps:** For the Yale AI Club's 20 navy hoodies in size M, it shows only 8 are on hand (12 short, $264 to restock at $22 each) and checks whether a proposed discount off the $58 list price still covers cost, so the Boss can approve a bulk discount that stays profitable.

### All tools

| Tool | Tables | Who can use it | Ticket(s) |
|---|---|---|---|
| `get_shop_date()` | desk | all agents | all |
| `list_tickets(status="open")` | tickets | all agents | all |
| `update_ticket(ticket_id, status, note, author)` | tickets (write) | Boss | all |
| `check_stock(sku, size=None)` | inventory | Inventory, Customer Service | 101, 103 |
| `check_bulk_order(sku, size, qty, discount_pct=0)` | inventory, pricing, vendors | Inventory, Accounting, Customer Service | 101, 103 |
| `list_vendors()` | vendors, invoices, desk | Boss, Inventory, Accounting | 101, 103 |
| `get_invoice_status(invoice_id)` | invoices, vendors, desk | Inventory, Accounting | 101 |
| `list_invoices(status="open")` | invoices, vendors, desk | Boss, Inventory, Accounting | 101, 103 |
| `get_rent_due(lease_id)` | leases, desk, cash_accounts | Accounting, Facilities | 102 |
| `get_cash_position()` | cash_accounts, approvals, payments | Boss, Accounting, Facilities | all |
| `prepare_payment(kind, ref_id, ticket_id, requested_by, reason, account)` | invoices or leases, cash_accounts, approvals (write) | Accounting, Facilities | 101, 102 |
| `prepare_purchase_order(vendor_id, sku, size, qty, ticket_id, requested_by, reason, account)` | inventory, pricing, vendors, invoices, cash_accounts, approvals (write) | Inventory, Accounting | 101, 103 |
| `list_approvals(status="pending")` | approvals | all agents | all |
| `save_customer_draft(ticket_id, recipient, subject, body, author)` | tickets, drafts (write) | Customer Service | 101, 103 |
| `list_drafts(ticket_id=None)` | drafts | Boss, Customer Service | 101, 103 |
| `approve_payment(approval_id, approved_by)` | approvals, cash_accounts, payments, invoices, leases, vendors (write) | **humans only** | 101, 102, 103 |
| `reject_payment(approval_id, rejected_by, reason)` | approvals (write) | **humans only** | 101, 102, 103 |

What the write tools do:
- **`prepare_payment` and `prepare_purchase_order`** only queue a row in `approvals` with status `pending`. No money moves.
  - The amount comes from the database (invoice amount, monthly rent, or qty × unit_cost), never from the agent.
  - They refuse anything the account balance cannot cover on its own.
  - They warn when pending approvals together exceed cash.
  - `prepare_payment` refuses a duplicate pending payment for the same invoice or lease.
- **`approve_payment`** is the only tool that moves money. It runs one database transaction:
  - It re-checks the balance and refuses the payment (and marks it `refused`) if cash would go negative.
  - It refuses a purchase order while the vendor still has an open invoice.
  - It subtracts the amount from `cash_accounts.balance` and inserts a `payments` row with `approved_by`.
  - It then updates the related record: the invoice becomes `paid`, the lease's `next_due` moves forward a month, or the purchase order gets its expected arrival date (today + `lead_days`).
  - It rejects any agent name as the approver.

### Working tables added by the server
These exist only in the working copy. `server.py` creates them if they are missing, and a reset removes them.

- **`approvals`**: payments and purchase orders waiting for a human.
  - Fields: kind, ref_id or vendor/sku/size/qty, amount, account, reason, requested_by, status (`pending` / `paid` / `rejected` / `refused`), decided_by, decided_at, decision_note, payment_id.
- **`drafts`**: customer messages that stay on the board.
  - Fields: ticket_id, recipient, subject, body, author, status `draft`, created_at.

## MCP connection (Claude Code)

The vibe coder is Claude Code. It reads MCP servers from a **project-scoped `.mcp.json`** in the folder the session is opened in, which is this HW5 folder:

```json
{
  "mcpServers": {
    "campus-customs": {
      "type": "stdio",
      "command": "python3",
      "args": ["mcp_server/server.py"]
    }
  }
}
```

The format:
- **`mcpServers`** is the required top-level key. It maps a server name to its launch settings.
- **`campus-customs`** is the server name. Claude Code shows the tools as `mcp__campus-customs__<tool>`.
- **`"type": "stdio"`** means Claude Code starts the server as a child process and talks to it over stdin/stdout. There is no port to manage.
- **`command` + `args`** is the command Claude Code runs from the project root. The path is relative so the config works for anyone who clones the repo. `server.py` finds the database from its own location (`data/campus_customs_new.db`), so it doesn't depend on the working directory.
- `python3` must be an interpreter with `fastmcp` installed (`pip install -r requirements.txt`).
- **Loading:** Claude Code reads `.mcp.json` only when a session starts. It asks once to approve a project server, and `/mcp` shows whether the server is connected.

## Agent team

The agents are built with PydanticAI in `backend/agents.py`. Every agent uses **`gpt-6-luna` through Portkey** (`PORTKEY_API_KEY`, OpenAI Responses API). The model name is a constant and can't be changed through settings.

Prompts live in `backend/prompts/`:
- Each agent has its own role file.
- `shop_rules.md` holds the shared shop rules and is added to every agent's prompt.

Data types are in `backend/models.py`.

| Agent | Prompt | Job | Returns |
|---|---|---|---|
| **Boss** | `boss.md` | Reads the ticket and the whole board, delegates by area, checks dependencies between tickets, decides, and sets the ticket status. | `BossDecision` |
| **Inventory** | `inventory.md` | Checks stock by SKU and size, finds shortfalls, picks a restock vendor by specialty and lead time, and checks whether that vendor is blocked by an unpaid invoice. | `AgentReport` |
| **Accounting** | `accounting.md` | Watches cash, invoices and pending approvals, checks margins and discounts, and queues payments and purchase orders for human approval. | `AgentReport` |
| **Facilities** | `facilities.md` | Reviews the lease and rent due date, checks whether cash covers it, and queues the rent payment for approval. | `AgentReport` |
| **Customer Service** | `customer_service.md` | Gets verified facts and the decision, then saves a customer draft. Never sends anything. | `AgentReport` |

**Agent loop:**
- `run_agent()` drives each agent with `Agent.iter()`. Each model response, tool call, tool result and retry is a loop step that gets audited.
- The Boss starts each ticket (`run_ticket`).
- A full run (`run_board`) resets the database and then works every open ticket in order.
- Command line: `python backend/run_tickets.py` runs the full board with a reset. `--ticket N` runs one ticket without resetting.

**Payments get queued, not just recommended.** Before the Problem 9 run, Accounting's prompt was tightened: if a payment is needed for the ticket and cash covers it, Accounting queues it even when only asked to "advise". The Boss now checks `list_approvals` before closing a ticket and sends any missing payment back to Accounting.

**Failure handling:** if a delegated agent fails (timeout, model error), `delegate` returns an error note to the agent that asked, which carries on and lists it as an open issue. Only running out of the ticket's token budget stops the whole run. Every error and cancellation is written to the audit trail.

**Full connectivity:**
- Every agent has a `delegate(to, task)` tool that can call any other agent.
- The other agent runs its own loop with its own tools and returns its report as the tool result.
- Delegation can't loop: an agent can't delegate to itself or to anyone above it in the current chain.

**Tools by role:**
- Each agent sees only the MCP tools its role needs (see "Who can use it" above).
- No agent can see `approve_payment` or `reject_payment`.

## Audit trail

`output/audit_trail.json` is a JSON list of `AuditRecord`s (see `backend/models.py`). New records are added to the end of the list and existing ones are never overwritten:
- Each write re-reads the file, appends, and atomically replaces it.
- An unreadable file is set aside as `audit_trail.corrupt-<time>.json`, never deleted.

Each record holds:
- `timestamp`, `run_id`, `ticket_id`
- `agent`, `depth`, and `chain` (who delegated to whom)
- `step`
- `event`: `start`, `model_response`, `tool_call`, `tool_result`, `retry`, `delegate`, `finish` or `error`
- `detail`: the prompt, tool name and arguments, tool result, delegated task, or final output
- `usage`: running request, tool-call and token counts for the ticket

Long text fields are cut to 2,000 characters.

**What's in the trail** (record positions, oldest first):

| Records | What |
|---|---|
| 0–43 | Problem 7 route testing: one ticket 102 run, plus test approve and reject decisions by Alice Liang. |
| 44–314 | Problem 8 dashboard testing: ticket 101 runs, including two that timed out before the model settings were fixed, plus one test approval. Each test is preceded by a `reset` record. |
| 315–386 | Problem 9, first attempt: ticket 101 after a reset. Accounting recommended paying invoice 501 but never queued it, so the prompts were tightened and the shop reset again. |
| 387–649 | **Problem 9 full run.** Reset (387), ticket 101 (388–471), ticket 102 (472–520), ticket 103 (521–571), four human decisions (572–575), ticket 103 re-run (576–649). |

Everything is kept on purpose as a record of testing. Only the last block counts toward the results.

## Safety (real customers and real money)

### Shop rules and where each is enforced

| Rule | Enforced by |
|---|---|
| `desk.date_today` is "today" | Code: every date tool computes overdue / days-until-due from `desk`. Prompt: `shop_rules.md` rule 1. |
| Lead times come from `vendors` | Code: `list_vendors` / `get_invoice_status` return `lead_days` and expected arrival. Prompt: rule 2. |
| A vendor with an open invoice won't ship | Code: `approve_payment` refuses a purchase order while the vendor has an open invoice. `list_vendors.can_ship` shows it. Prompt: rule 3. |
| Human approval for every payment, and records updated when paid | Code: agents only have `prepare_*`. `approve_payment` is hidden from agents and is the only path that subtracts cash and writes `payments`, `invoices`, `leases` and `approvals`. Dashboard: "Approve & pay" needs a typed name. |
| Refuse when cash is short; never go negative | Code: checked at queue time and again inside the approval transaction. A refused approval is marked `refused`. |
| Cash only goes out | Code: no tool adds money. Prompt: rule 6. |
| Verified data only, through MCP | Code: agents have no tools except the MCP server and `delegate`. Prompt: rule 7. |
| No customer emails or vendor contact | Code: no sending tool exists. Drafts are stored with status `draft`. Prompt: rule 8 and the Customer Service prompt. |
| Reset before a full run | Code: `run_board()` and the dashboard's "Reset shop" (`POST /api/reset`) copy the original database. A `reset` record goes in the audit trail. |

### Safeguards

- **A human approves every payment.** Agents can only queue approvals. The tools that execute or reject a payment are hidden from all agents and refuse an agent's name as the approver. Every payment row records `approved_by`.
- **No negative balances.** Payments are refused at both queue time and approval time if cash can't cover them. Approval re-checks the balance inside the same transaction that subtracts it.
- **Amounts come from the database.** Agents can't type in a payment amount, so a confused or manipulated model can't overpay.
- **Vendor rule is enforced in code.** A purchase order can't be approved while the vendor has an open invoice.
- **No outbound contact.** There is no email or messaging tool. Customer messages are drafts a human must review. The Customer Service prompt keeps internal details (unpaid bills, cash) out of drafts and forbids promising unconfirmed dates. Prompts aren't guarantees: in the full run, draft 1 still mentioned the pending invoice approvals, which is one reason a human reviews every draft.
- **Least privilege.** Each agent sees only the tools its role needs. For example, Customer Service can't queue payments, and only the Boss changes ticket status.
- **Verified data only.** Prompts require every fact to come from an MCP tool, and the audit trail lets a human check each claim against the tool result behind it.
- **Reversible test environment.** All writes go to `campus_customs_new.db`. The original stays untouched and a full run starts with a reset.
- **Before going live with real money:**
  - Add login for approvers rather than a typed name.
  - Add per-payment and per-day spending caps.
  - Require two approvers above a threshold.
  - Treat customer-submitted ticket text as untrusted, since it could try to instruct the agents.
  - Have a human send every customer message from a real mailbox.

## Token limits

Set in `backend/agents.py`:

| Control | Value | Why |
|---|---|---|
| `TICKET_LIMITS.request_limit` | 40 model requests per ticket | Shared by the Boss and every delegated agent through one shared usage counter. |
| `TICKET_LIMITS.tool_calls_limit` | 60 tool calls per ticket | Stops tool-call loops. |
| `TICKET_LIMITS.total_tokens_limit` | 400,000 tokens per ticket | Hard ceiling on spend for one ticket. |
| `MAX_DELEGATION_DEPTH` | 2 | Boss → specialist → one more specialist, no deeper. |
| `MAX_DELEGATIONS_PER_TICKET` | 8 | Caps how many sub-agents one ticket can start. |
| One delegation at a time | lock per agent | An agent's parallel hand-offs wait their turn. The prompts tell the Boss to start with the owning agent and let it consult others, rather than fanning out to everyone. |
| `openai_reasoning_effort` | `none` | With reasoning on (even `low`), one Facilities step reproducibly reasoned until the 120 s timeout. With `none` the same step takes about 1–6 s and about 200 output tokens. |
| `max_tokens` | 3,000 per model call | Hard cap on output per step, so a runaway answer stops instead of burning tokens. |
| `MODEL_TIMEOUT_S` | 120 s, 1 retry | One stuck call can't stall the board. |
| Role-filtered tools | 6–11 MCP tools per agent, plus `delegate` | Smaller tool lists mean shorter prompts. |
| Prompts | "ask once with a complete task", "don't repeat a tool call" | Fewer round trips. |

Measured on test runs:
- Ticket 102: about 22k tokens, 9 requests.
- Ticket 103: about 54k tokens, 20 requests.
- Ticket 101 (from the dashboard, after the fixes above): about 55k tokens, 19 requests, 100 s.

## Backend routes

The FastAPI app is `backend/main.py`. Start it from `backend/` with `uvicorn main:app --reload --port 8000` (use the `.venv` Python), and it serves `http://localhost:8000`. Every route reads and writes the shop through the MCP server.

- `GET /api/tickets`: all tickets with their current status, customer drafts, approvals, and the latest agent-run result.
- `POST /api/tickets/{ticket_id}/run`: starts the agent team (the Boss first) on one ticket in the background and returns a `run_id`. Only one run at a time (409 if busy).
- `GET /api/events?since=&ticket_id=&run_id=`: recent agent events from `output/audit_trail.json` (who said what, which tools ran, delegations, human decisions). Poll with the returned `next`.
- `GET /api/approvals?status=pending`: payments and purchase orders the agents prepared for a human.
- `POST /api/approvals/{approval_id}/approve` (`{"approved_by": "<name>"}`): a human approves a prepared payment or purchase order.
  - This is the only route that moves money. It subtracts the cash, records the payment, and updates the invoice, lease, or purchase order.
  - It refuses payments that would make the balance negative.
  - Once no approvals for the ticket are still pending, it marks the ticket resolved.
- `POST /api/approvals/{approval_id}/reject` (`{"rejected_by", "reason"}`): a human rejects a prepared payment. No money moves, and the ticket goes back to in progress.
- `GET /api/cash`: the checking balance from `cash_accounts`, plus money queued for approval and payments made.
- `POST /api/reset`: copies `data/campus_customs.db` over the working copy for a fresh run. The audit trail is kept, and a `reset` record is added so earlier runs no longer count as the tickets' current state. Refused while a run is in progress.

CORS allows the Vite dev server (`http://localhost:5173`, or the next free local port Vite picks).

Each ticket's latest run (`last_run`) is rebuilt from the audit trail since the last reset, so it survives a backend restart.

## Dashboard

The React + Vite + TypeScript dashboard is in `frontend/`. Start it with `npm run dev` from that folder. It calls `http://localhost:8000`, or `VITE_API_URL` if set. The full design write-up is in `output/design.md`.

| Part | What it shows / does | Backend route |
|---|---|---|
| Ticket board (left) | Three ticket cards with status chips, a RESOLVED stamp when the run is done, and *Send the crew* / *Run again* buttons | `GET /api/tickets`, `POST /api/tickets/{id}/run` |
| Crew map (center) | The five agents as CSS critters on a fully connected graph. Delegation edges light up for the selected ticket's run, and the active agent glows. | `GET /api/events` |
| Live feed (center) | Agent bubbles, hand-off cards, clickable tool chips (arguments and result), final reports, human decisions, and a "who is working" indicator | `GET /api/events` (polled every 1.2 s while running) |
| Approvals tab (right) | Pending payments and purchase orders with the balance after each, *Approve & pay* and *Reject (reason)*, and recent decisions | `GET /api/tickets` (approvals), `POST /api/approvals/{id}/approve`, `.../reject` |
| Crew summary tab | The Boss's final call, plus each agent's report, hand-offs, tools used, and changes made. Token usage for the run. | `GET /api/events`, `GET /api/tickets` |
| Drafts tab | Customer drafts as postcards stamped "Draft · not sent" | `GET /api/tickets` (drafts) |
| Cash meter (top) | Checking balance (counts down after a payment), pending total, cash left after approvals, and a ledger of payments | `GET /api/cash` |
| Reset shop (top) | Two-click reset of the working database | `POST /api/reset` |

## Full run results (Problem 9)

The working database was reset from the dashboard at 2026-10-14 23:48:37, and each ticket was run from the dashboard. Details are in `output/desk_tickets.html`, `output/resolved_tickets.json` and `output/resolved_board.html`.

| Ticket | Agents (in order) | Human decisions | Cash impact | Final DB status |
|---|---|---|---|---|
| 101 | Boss → Inventory → Accounting → Boss → Customer Service | #1 invoice 501 $840 approved; #2 purchase order 1 tee $8 approved | −$848.00 | `resolved` |
| 102 | Boss → Facilities → Accounting → Boss | #3 rent lease 1 $2,400 approved | −$2,400.00 | `resolved` |
| 103 | Run 1: Boss → Inventory → Accounting → Boss. Re-run: Boss → Inventory → Accounting → Boss → Customer Service | #4 purchase order 12 hoodies $264 rejected (not enough cash) | $0.00 | `in_progress` (12 units unfunded; run complete) |

**Checking: $3,400.00 → $152.00.** The three payments total $3,248.00 and match `cash_accounts.balance` = 152.0 and the 3 rows in `payments`.

Tokens: 71,047 (101) + 37,061 (102) + 46,632 + 61,344 (103, two runs) = 216,084 for the full run.
