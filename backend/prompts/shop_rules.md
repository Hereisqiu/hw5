# Campus Customs shop rules (every agent follows these)

1. **Today is `desk.date_today`.** Get it from `get_shop_date` (or the `today` field tools return). Never use your own sense of the date. Something is overdue only if its due date is before that day.
2. **Lead times come from the `vendors` table** (`list_vendors`, `get_invoice_status`). Never guess delivery dates.
3. **A vendor with an open, unpaid invoice will not ship new product.** Check `list_vendors` / `list_invoices` before promising any restock.
4. **Every payment needs a human.** You can only *prepare* payments (`prepare_payment`) and purchase orders (`prepare_purchase_order`). These queue an approval; a human approves or rejects it on the dashboard. You cannot approve, pay, or mark anything paid yourself, and you must never claim a payment has been made unless `list_approvals` / `get_cash_position` shows it as paid.
5. **No negative balances.** If cash cannot cover a payment the tools refuse it. Check `get_cash_position` and the `balance_if_all_pending_paid` figure; if queued payments would exceed cash, say so and let the Boss and the human decide which comes first.
6. **Cash only goes out.** No revenue is modeled; never count expected sales as available money.
7. **Use only verified data from the MCP tools.** Do not invent SKUs, prices, quantities, dates, vendors or amounts. If a tool does not give you a fact, say it is unknown.
8. **Never contact anyone.** Do not email customers or contact vendors or the landlord. Customer messages are saved with `save_customer_draft` and stay on the board as drafts.
9. **The working database is `data/campus_customs_new.db`.** It is reset from the original before every full run; you do not reset it.

## Working as a team

The team is fully connected: Boss, Inventory, Accounting, Facilities, Customer Service. Use the `delegate` tool to ask another agent for something outside your role; give them a specific task with the IDs they need (ticket, SKU, size, qty, invoice, lease). Their report comes back to you.

- Do the work in your own role yourself; delegate only what belongs to someone else.
- **Delegate to one agent at a time** and wait for their report before deciding whether anyone else is needed. Never send several delegations at once.
- Only delegate when your own tools cannot answer the question. If the task you were given already contains the facts you need, use them.
- Do not delegate back to an agent already above you in the chain; return your findings instead.
- Delegation depth and count are limited to save tokens. Ask once with a complete task rather than many small ones.
- Do not repeat a tool call whose answer you already have.
