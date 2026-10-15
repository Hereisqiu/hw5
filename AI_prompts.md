# AI Prompts — Homework 5: Campus Customs Multi-Agent Operations

This file records the prompts I typed to my vibe coder (Claude Code), one section per problem.

## Problem 1: Vibe Coder Prompts

**Prompt:**
> I will create an `AI_prompts.md` file at the start of the assignment and update it as I work. This file will log the prompts I give you, my vibe coder, describing each problem in my own words.
> I will organize the file into one section per problem, each including:
>
> * Problem number and title
> * Initial prompt: At least one prompt I typed, using my own words as much as possible.
> * Follow-up prompt (if needed): The follow-up prompt and one sentence explaining what was missing from the initial response.

**Follow-up:** None needed.

## Problem 2: Explore the Campus Customs Database

**Prompt:**
> Open `data/campus_customs.db` and examine all tables and their fields. Make a copy of the original database as `data/campus_customs_new.db`, which I will use for updates in later problems.
>
> Review the three open tickets and understand how they connect to other tables.
>
> Create `output/harness.md`, listing each table’s fields and briefly explaining its relevance to the agents.
>
> I will continue updating this harness file in subsequent problems.

**Follow-up:** None needed.

## Problem 3: Build the MCP Server

**Prompt:**
> Create an MCP server in `mcp_server/` using FastMCP, connected to `data/campus_customs_new.db`. There is no need to connect or run the server yet.
> All agents in this assignment will use this server's tools, and I will add more later. For now, implement three clearly named tools relevant to the existing tickets. Use only data from the database without inventing information.
> Update `output/harness.md` to document each tool, including:
>
> * The table it reads.
> * The ticket it supports (101, 102, or 103).
> * One specific sentence explaining how the tool helps resolve that ticket, rather than a generic description.
>
> Also create a brief `mcp_server/README.md` explaining the server's purpose, the database it uses, and its three tools.

**Follow-up:** None needed.

## Problem 4: Connect and Test the MCP Server

**Prompt:**
> Connect the MCP server to this project through my vibe coder (Claude Code, Codex, or Cursor), so it can access the tools. Save the connection configuration as `.mcp.json` in the project root, or use the vibe coder’s equivalent local MCP configuration format.
> Once connected, test all three MCP tools and save the results in `output/mcp_smoke.json`. For each tool, include:
>
> * The prompt I gave the vibe coder.
> * The tool name.
> * The tool's actual output, verified against `data/campus_customs_new.db`.
>
> Clarify the required MCP configuration format

**Follow-up:**
> Please complete Problem 4's missing MCP smoke test now that the session is in the HW5 folder.
> Use the `campus-customs` MCP server to execute these three prompts:
>
> 1. "Use `get_invoice_status` to check the current status of invoice 501."
> 2. "Use `get_rent_due` to check the rent details for lease 1."
> 3. "Use `check_bulk_order` to evaluate an order of 20 `CC-HOOD-NAVY` hoodies in size M with a 10% discount."

What was missing: the first attempt only created `.mcp.json` and documented the format. Claude Code loads MCP servers when a session starts, and my session had started in the parent folder, so the smoke test couldn't run until the session was moved into the HW5 folder.

**Smoke-test prompts** (recorded with tool outputs in `output/mcp_smoke.json`):
> Use `get_invoice_status` to check the current status of invoice 501.

> Use `get_rent_due` to check the rent details for lease 1.

> Use `check_bulk_order` to evaluate an order of 20 `CC-HOOD-NAVY` hoodies in size M with a 10% discount.

## Problem 5: Build the Agent Team and Expand MCP Tools

**Prompt:**
> Build a fully connected Campus Customs agent team using PydanticAI, with five agents: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so any agent can delegate work to another.
> Store each agent's prompt in a separate file under `backend/prompts/`, define data types in `backend/models.py`, and place agent implementations under `backend/`. Use `PORKEY_API_KEY` and only `gpt-6-luna` through Portkey for every agent.
> 1. Agent Prompts
> Write detailed prompts for each agent based on their responsibilities and the shop's rules:
> Boss (`backend/prompts/boss.md`)
> You oversee the shop's operations. Review open tickets, determine what needs to be done, and delegate tasks to the appropriate agents. Coordinate across agents when tickets involve multiple areas, consider dependencies between tickets, and make final decisions based on verified information. Require human approval for payments and keep track of unresolved issues.
> Inventory (`backend/prompts/inventory.md`)
> You manage product availability and restocking. Check inventory by SKU and size, identify shortages, and determine which vendors can supply missing products. Use vendor lead times and check for unpaid invoices, since vendors cannot ship until outstanding invoices are settled. Work with Accounting when restocking involves financial decisions and report feasible options to the Boss.
> Accounting (`backend/prompts/accounting.md`)
> You handle the shop's finances. Check cash balances, invoices, payments, product costs, and margins. Evaluate outstanding bills, proposed purchases, and discount requests. Use the shop's official date to identify overdue payments. Prepare payments or purchase orders for human approval, never execute payments without approval, and refuse transactions that would create negative cash balances. Coordinate with other agents when financial decisions affect their work.
> Facilities (`backend/prompts/facilities.md`)
> You manage the shop's lease and rent obligations. Review lease terms, payment amounts, and due dates. Use the shop's official date to identify upcoming or overdue rent. Work with Accounting to assess payment feasibility, prepare payments for human approval, and inform the Boss of any issues requiring attention.
> Customer Service (`backend/prompts/customer_service.md`)
> You prepare customer communications based on verified shop information. Consult Inventory about product availability and fulfillment, Accounting about pricing and discounts, and the Boss about final decisions. Draft clear responses explaining order status, shortages, delays, or discount decisions. Never promise unconfirmed outcomes or send messages directly. All communications must remain drafts on the board.
> 2. Shop Rules
> Make sure all agents follow the relevant rules:
>
> * Use `desk.date_today` as the shop's current date.
> * Get vendor lead times from the `vendors` table.
> * Vendors cannot ship new products while they have open unpaid invoices.
> * Require human approval before making any payment, and update the relevant database records when an approved payment is completed.
> * Refuse payments when available cash is insufficient. Never allow negative balances.
> * Assume cash only flows out, since revenue is not modeled.
> * Use only verified database information accessed through MCP tools.
> * Do not send customer emails or contact vendors. Keep communications as drafts.
> * Reset the working database to its original values before a full ticket-resolution run.
>
> 3. MCP Tools and Agent Collaboration
> Add any tools the agents need to the existing MCP server to work on tickets 101, 102, and 103.
> Ensure all five agents can delegate tasks to one another as needed. All shop information must come through the MCP server connected to `data/campus_customs_new.db`. Do not create a separate shop-tools layer that bypasses MCP.
> 4. Audit Trail
> Configure the agents to append records to `output/audit_trail.json` as they run. Record enough information for each agent-loop step to audit its actions and decisions later. Preserve existing records rather than overwriting the file on each run.
> 5. Documentation
> Update `output/harness.md` to include:
>
> * All five agents.
> * Every MCP tool, including those added in this problem, and the database table(s) each uses.
> * A brief safety section covering appropriate safeguards when agents interact with real customers and money.
> * Limits to control token usage.
>
> Update `mcp_server/README.md` so the tool list reflects all currently implemented tools.
> Keep the implementation focused on these requirements and consistent with the existing project. Avoid unnecessary features or complexity.

**Follow-up:** None needed.

## Problem 6: Plan the Three Tickets

**Prompt:**
> Before running the backend agents, create `output/desk_tickets.html` as a standalone HTML page that I can open by double-clicking.
> Include five tabs: Ticket 101, Ticket 102, Ticket 103, Cash, and Reflection. Leave Cash and Reflection empty or with a short placeholder for later problems.
> For each ticket, create an Expected section based on my plans below, and reserve an empty Actual section for results after the agents run.
> Ticket 101: Customer Order
>
> * Boss first delegates to Inventory to check the requested product's stock and restocking options.
> * Inventory consults Accounting about the vendor's unpaid invoice and whether payment is feasible.
> * Accounting reports the financial situation and prepares any necessary payment for human approval.
> * Boss reviews the findings and decides how to proceed.
> * Customer Service drafts a response explaining the order's status and any confirmed fulfillment options.
>
> Ticket 102: Rent
>
> * Boss first delegates to Facilities to review the lease, rent amount, and due date.
> * Facilities consults Accounting to check available cash and prepare the rent payment for human approval.
> * Boss reviews the findings and determines the next action.
>
> Ticket 103: Bulk Discount Request
>
> * Boss first delegates to Inventory to verify available stock and identify any shortage or restocking needs.
> * Inventory consults Accounting to assess product costs, margins, discount feasibility, and relevant financial constraints.
> * Boss reviews the findings and decides what discount, if any, can be offered.
> * Customer Service drafts a response reflecting the Boss's decision and realistic fulfillment options.
>
> For each Expected section, clearly explain why the Boss calls the first agent, list the anticipated delegations in order, and identify the specific MCP tools expected to be used. Use the actual tool names implemented in the existing MCP server rather than inventing new ones.
> Keep the plans grounded in the database and the shop's rules. Do not send every specialist to every ticket unless their involvement is necessary.
> Do not run the agents or fill in the Actual sections yet. I will compare these expectations with their actual behavior in later problems.

**Follow-up:** None needed.

## Problem 7: Build the Backend Routes

**Prompt:**
> Create a FastAPI backend in backend/main.py with routes that the React dashboard can use in the next problem.
> Implement routes to:
>
> * Return all three tickets and their current status (open or resolved).
> * Accept a ticket ID and run the agent team to handle that ticket.
> * Return recent agent events, including what each agent said and which tools it used, so the dashboard can refresh.
> * Execute a payment or purchase only after a human approves it. Agents should only prepare these actions; this approval route is responsible for updating the cash balance.
> * Retrieve the current checking balance from cash_accounts.
> * Reset the working database to its original values for a fresh run.
>
> Make sure the backend can be started from the backend/ directory using:
> uvicorn main:app --reload --port 8000
> The server should then be accessible at http://localhost:8000 for the frontend to call.
> Update output/harness.md with a one-line description of each route, including its URL and purpose.

**Follow-up:** None needed.

## Problem 8: Build the Agent Dashboard

**Prompt:**
> Create a frontend dashboard in frontend/ using React, Vite, and TypeScript. Connect it to the FastAPI backend routes from Problem 7.
> The dashboard should:
>
> * Display all three tickets.
> * Let me select a ticket and start the agent team to work on it.
> * Show each agent's messages and actions as the ticket runs.
> * Mark tickets as resolved when their runs finish.
> * Provide a brief summary of what each agent did for the selected ticket.
> * Allow human approval of payments or purchases when requested.
> * Display the current checking balance and update it after approved payments.
>
> Design the dashboard to be visually appealing, intuitive, and engaging. Be creative with the layout and overall experience so it feels like a practical workspace people would enjoy using.
> Configure the frontend to communicate with http://localhost:8000. Enable CORS on the backend for the Vite frontend origin, typically http://localhost:5173, so browser requests are allowed.
> Make sure the frontend can be started from frontend/ using:
> npm run dev
> This should launch the React dashboard in the browser, where I can select tickets and observe the agents working.
> Create output/design.md explaining the dashboard's design choices, including its layout, how agents are visually distinguished, how resolved tickets and cash balances are displayed, and the creative details that make the interface distinctive and enjoyable to use.

**Follow-up:** None needed.

## Problem 9: Resolve the Three Tickets

**Prompt:**
> Before running all three tickets, reset data/campus_customs_new.db to its original state and record the starting checking balance. Then use the dashboard to run tickets 101, 102, and 103 until all three are resolved.
> Update output/desk_tickets.html from Problem 6:
>
> * For each ticket, complete the Actual section using results from the run, including which agents participated, their delegations, and the MCP tools they used.
> * Preserve the Expected sections so I can compare planned and actual behavior.
> * On the Cash tab, record the starting checking balance after the reset, each ticket's cash impact (including the reason, payment or purchase, and dollar amount), and the ending balance. Verify that the ending balance exactly matches cash_accounts in the working database.
>
> Also create or update these files:
>
> * output/resolved_tickets.json: For each ticket, include its ID, final status, brief outcome, each agent's contribution, and any human approvals.
> * output/resolved_board.html: Create a standalone HTML page that I can open by double-clicking, containing a screenshot of the React dashboard for each resolved ticket (101, 102, and 103).
> * output/audit_trail.json: Append records from the actual agent runs without overwriting previous entries.
> * output/harness.md: Complete the documentation to cover all database tables, MCP tools, five agents, API routes, dashboard, and safety rules.
>
> Make sure all recorded outcomes reflect the actual runs, and double-check the cash calculations against the database. Do not invent agent actions, approvals, or financial transactions.

**Follow-up:** None needed.

## Problem 10: Reflection

**Prompt:**
> Open `output/desk_tickets.html` and complete the Reflection tab. Use the latest `audit_trail.json`, `resolved_tickets.json`, `resolved_board.html`, `harness.md`, and the Expected, Actual, and Cash tabs as evidence.
> Write detailed, thoughtful reflections in my first-person voice. I want to evaluate not only whether the agents followed instructions, but whether their decisions made sense for Campus Customs as a real business, especially when multiple tickets competed for the same limited cash.
> Address all five questions below.
> 1. How would I evaluate the agents' performance on each ticket, and why?
> Ticket 101: Tauhid Zaman's Bulldog tee
> Evaluate how Boss, Inventory, Accounting, and Customer Service handled the out-of-stock size S tee, overdue $840 invoice 501, and Bulldog Print Co's shipping restriction.
> Discuss how Accounting went beyond my initial expectation by preparing both the $840 invoice payment and a separate $8 purchase order. Both received human approval, bringing the ticket's total cash impact to $848. Customer Service saved a draft explaining the shortage and conditional September 5 arrival without sending it.
> Also discuss the earlier failed attempt, when the agents recommended paying the invoice but did not actually queue the approval. Explain what this reveals about the difference between identifying the right action and executing it through the correct tool.
> Ticket 102: Chapel Street rent
> Evaluate how Boss, Facilities, and Accounting handled the $2,400 rent due September 2. Facilities correctly verified that the payment was due in two days, not overdue. Accounting considered the $848 already committed to ticket 101, prepared approval #3, and recognized that paying both obligations would leave only $152.
> The human approved the rent, and the lease's next due date moved to October 2. Discuss the agents' accuracy and financial awareness, while considering whether three agents were necessary for a relatively straightforward transaction.
> Ticket 103: Yale AI Club hoodie discount
> Evaluate how the agents balanced customer value, profitability, inventory, vendor restrictions, and liquidity.
> Inventory identified eight hoodies available against 20 requested, leaving 12 to restock for $264. Accounting confirmed the $22 unit cost and $58 list price. The Boss recommended a 10% discount, giving a $52.20 selling price, $1,044 total revenue, and $30.20 unit margin before other expenses.
> However, approval #4 for the $264 restock was rejected because only $152 would remain after the other payments, a $112 shortfall.
> Discuss the important distinction between the first run, which recommended the discount and queued the restock but did not save a customer draft, and the second run, which responded to the human rejection by saving draft #2. The draft offered the eight available hoodies without promising delivery of the remaining 12.
> Evaluate this as a partially successful outcome: the team made a financially responsible decision and communicated an alternative, but the original 20-hoodie request remained unfulfilled and the database ticket stayed `in_progress`.
> 2. For each ticket, how did Actual compare with my Expected plan?
> Compare the original Expected and updated Actual sections, addressing:
>
> * Whether the agents followed my anticipated delegation sequence.
> * Which tools and approvals were used as expected.
> * Any unexpected actions, omissions, additional runs, or human interventions.
> * Whether the final business outcome matched my prediction.
> * What I learned from each difference.
>
> For ticket 101, emphasize the additional $8 purchase order, which I had not expected because I assumed invoice 501 already covered the reprint.
> For ticket 102, emphasize how the rent process largely matched expectations but incorporated the additional $8 commitment from ticket 101.
> For ticket 103, emphasize the difference between preparing a purchase order and actually being able to fund it. Explain why the rejected approval, second agent run, and revised customer draft were important departures from the original plan.
> Use the final cash reconciliation as concrete evidence:
>
> * Starting checking balance: $3,400
> * Invoice 501: $840 approved and paid
> * One-tee purchase order: $8 approved and paid
> * Rent: $2,400 approved and paid
> * Total paid: $3,248
> * Ending checking balance: $152
> * Hoodie restock: $264 rejected, with no cash deducted
>
> Distinguish the shop's simulated date of August 31 from the actual October 14 execution timestamps. Do not double-count earlier attempts or resets.
> 3. What would have been simpler with one agent using tools, and why?
> Use ticket 102 as the clearest example. A single agent with access to `get_rent_due`, `get_cash_position`, `list_approvals`, and `prepare_payment` could have verified the lease, checked liquidity, and prepared the payment without multiple handoffs.
> Discuss how this could reduce repeated tool calls, latency, token usage, and coordination overhead.
> Also consider whether parts of ticket 101, such as checking stock and identifying the overdue invoice, could have been combined.
> Contrast these simpler workflows with ticket 103, where specialized perspectives from Inventory, Accounting, and Customer Service helped the Boss balance competing operational and financial considerations.
> Importantly, explain that using one agent should not eliminate human approval or the separation between preparing and executing payments.
> 4. Describe three new problems Campus Customs could solve with my existing agents and tools.
> Choose three realistic scenarios that demonstrate different capabilities:
>
> 1. Another vendor payment blocking a customer order. Explain how Inventory could identify unavailable stock and a blocked supplier, Accounting could check the invoice and prepare payment, and Customer Service could draft an update, similar to ticket 101.
> 2. A new student organization's bulk merchandise request. Explain how Inventory could check stock, Accounting could calculate discount margins and restock costs, and Boss could decide whether to offer a discount, building on ticket 103.
> 3. A future rent notice competing with other expenses. Explain how Facilities and Accounting could verify the lease, compare available cash with pending commitments, and request human approval, as in ticket 102.
>
> For each scenario, identify the relevant existing agents, specific tools, likely delegation sequence, and expected outcome. Stay within what the current tools can actually do.
> 5. Describe three new problems Campus Customs could not solve with my current tools.
> Choose three realistic gaps and explain the additional capabilities needed:
>
> 1. Customer returns and refunds. The current system can record outgoing approved payments for supported expense types, but it cannot verify a customer's original purchase, process returns, calculate refunds, or update returned inventory. Propose tools for order lookup, return validation, refund processing, and inventory adjustments, potentially supported by a Returns agent.
> 2. Demand forecasting and proactive inventory planning. The current Inventory agent can identify stock shortages but lacks historical sales analysis, demand forecasting, and reorder optimization. Propose tools to retrieve historical transactions, forecast demand, calculate reorder points, and evaluate inventory carrying costs. Explain how a Planning or Forecasting agent could work with Inventory and Accounting.
> 3. Tracking shipments and resolving delivery delays. The current system estimates arrival dates using vendor lead times but cannot verify whether products were dispatched, track shipments, or detect delays. Propose tools for vendor order status, shipment tracking, delivery confirmation, and customer notifications. Explain how a Logistics agent could coordinate with Inventory and Customer Service.
>
> For each, explicitly distinguish what the current tools can do from what the new tools would add.
> Writing and implementation requirements
> Write in my natural first-person voice, with thoughtful, specific reasoning. Avoid generic AI essays, exaggerated praise, and repetitive statements.
> I want the reflection to show that I understand both the technical design and the operational consequences of the agents' decisions. In particular, explore these lessons where relevant:
>
> * A correct recommendation is not the same as a completed tool action.
> * Multiple individually affordable payments may collectively exceed available cash.
> * Human approval is a meaningful financial safeguard, not just a procedural step.
> * A completed agent run does not necessarily mean the customer's problem has been resolved.
> * Specialization improves decision quality when tasks require different expertise, but unnecessary delegation adds overhead.
> * An effective agent system must adapt to human decisions, as ticket 103 demonstrated after the restock rejection.
>
> Ground every observation in the three actual tickets, using exact amounts, tool names, agent actions, and outcomes. Do not invent additional actions or claim that drafts were sent.
> Keep the reflection detailed and thorough, but concise enough that every paragraph adds meaningful analysis.
> Implementation: Only fill the Reflection tab in `output/desk_tickets.html`. Preserve all existing Expected, Actual, and Cash content, HTML structure, styling, navigation, and functionality. Do not modify other files or rerun the agents.

**Follow-up:** None needed.

## Problem 11: Submit to GitHub

**Prompt:**
> Push my code to a public GitHub repository so graders can clone it. Save the repository URL in `output/github_url.txt` and give me the same URL to submit on Canvas.
> Do not upload my real `.env` file. Make sure both database files are included under `data/`: the original database and the working copy.
> Follow the expected file structure shown in `Pasted Graphic 1.png`.
> In the README, explain how to:
>
> * Copy the original database to the working copy for a clean run.
> * Start the MCP server.
> * Start the FastAPI backend.
> * Launch the React board.
> * Reset the database before running all three tickets.

**Follow-up:**
> before pushing make sure: Environment variables: Do not commit my real .env file or any API keys to GitHub. Add .env to .gitignore and include a .env.example file containing the required environment variable names with placeholder values, but no actual credentials. In the README, explain how to copy .env.example to .env and fill in the necessary values before running the project.

What was missing: the first prompt only said not to upload `.env`, so it didn't require a placeholder `.env.example`, a `.gitignore` entry, a check for API keys, or README steps for creating `.env`.
