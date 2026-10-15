# Campus Customs Multi-Agent Operations (HW5)

A five-agent team runs the **Campus Customs** shop's ticket board. A human watches and approves payments from a React dashboard.

- **MCP server** (`mcp_server/server.py`, FastMCP): the only way agents read or change shop data. It works on `data/campus_customs_new.db`.
- **Agent team + API** (`backend/`, FastAPI + PydanticAI):
  - Agents: Boss, Inventory, Accounting, Facilities, Customer Service.
  - They're fully connected: any agent can delegate to any other.
  - Every agent uses `gpt-6-luna` through Portkey.
  - Each step is appended to `output/audit_trail.json`.
- **Dashboard** (`frontend/`, React + Vite + TypeScript): the ticket board, a live agent feed, the crew map, approvals, the cash meter, and customer drafts.

Agents can only **prepare** payments and purchase orders. Money moves only when a human clicks **Approve & pay**, and a payment that would make the balance negative is refused. Customer messages stay as drafts and are never sent.

```
hw5/
├── AI_prompts.md            prompts I gave my vibe coder, one section per problem
├── requirements.txt         Python dependencies
├── .env.example             template for .env (placeholder values only)
├── .gitignore               keeps .env, .venv and node_modules out of git
├── .mcp.json                Claude Code MCP config (campus-customs server)
├── data/
│   ├── campus_customs.db       original database (never modified)
│   └── campus_customs_new.db   working copy used by the MCP server and backend
├── mcp_server/              server.py + README.md
├── backend/                 main.py (API), agents.py, models.py, audit.py, run_tickets.py, prompts/*.md
├── frontend/                React dashboard
└── output/                  harness.md, desk_tickets.html, design.md, resolved_*.{json,html}, audit_trail.json, …
```

> **Note:** the committed `data/campus_customs_new.db` holds the **end state of my graded run** (checking $152.00 after three approved payments). Reset it (step 3) before starting a fresh run.

## 1. Install

Requires Python 3.11+ and Node 20+.

```bash
cd hw5
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Set up environment variables (.env)

The API key is **not** in this repo. `.env` is listed in `.gitignore`, and only the placeholder template `.env.example` is committed.

1. Copy the template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and replace the placeholder with your real key:

   | Variable | Required | What to put |
   |---|---|---|
   | `PORTKEY_API_KEY` | yes | Your Portkey API key. Every agent calls `gpt-6-luna` through the Portkey gateway with it. |

3. Never commit `.env`. `git status` should not list it.

The backend reads `.env` from the project root, and also from any parent folder.

## 3. Copy the original database to the working copy (clean run)

`data/campus_customs.db` is the untouched original. Everything writes to `data/campus_customs_new.db`. To start clean, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

## 4. Start the MCP server

The backend starts the MCP server for you as a stdio child process, so you don't need to run it separately for the dashboard. To run or inspect it on its own:

```bash
python mcp_server/server.py            # stdio (what .mcp.json and the backend use)
python mcp_server/server.py --http     # HTTP at http://127.0.0.1:8002/mcp
```

To use the tools from **Claude Code**, open Claude Code in this folder. It reads `.mcp.json` and asks you to approve the `campus-customs` server once. Run `/mcp` to check it's connected. The `python3` it launches must have the requirements installed, so start Claude Code from the activated `.venv`. See `mcp_server/README.md` for the 17 tools.

## 5. Start the FastAPI backend (port 8000)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API routes are listed in `output/harness.md` → *Backend routes*. A quick check: http://localhost:8000/api/cash.

## 6. Launch the React board (port 5173)

In a second terminal:

```bash
cd frontend
npm install                            # first time only
npm run dev
```

Open the URL Vite prints, usually http://localhost:5173. The board calls the backend at `http://localhost:8000`; set `VITE_API_URL` to change it. If 5173 is busy, Vite picks the next port, and the backend accepts any `localhost` port.

## 7. Reset the database, then run all three tickets

Before a full run, always reset the working database to the original values. Either:

- click **Reset shop** in the dashboard's top bar (click twice to confirm), or
- call the API: `curl -X POST http://localhost:8000/api/reset`, or
- copy the file as in step 3 (with the backend stopped).

A reset puts checking back to **$3,400.00** and all tickets back to `open`. The audit trail is kept, and a `reset` record is added to it. Then, on the dashboard:

1. Type your name in **Approving as** (Approvals tab).
2. Click **Send the crew** on ticket 101, then 102, then 103. Watch the live feed and crew map; one ticket runs at a time.
3. Review the queued payments in **Approvals** and choose **Approve & pay** or **Reject**. The cash meter updates after each one.

Command-line alternative (no dashboard, no approvals):

```bash
cd backend
python run_tickets.py                  # resets the database, then the Boss works every open ticket
python run_tickets.py --ticket 101     # one ticket, no reset
```

## Documentation

- `output/harness.md`: tables, MCP tools, agents, routes, dashboard, safety rules, token limits, and full-run results.
- `output/desk_tickets.html`: Expected vs Actual for each ticket, the Cash reconciliation, and the Reflection (open by double-clicking).
- `output/resolved_board.html`: dashboard screenshots of the three resolved tickets.
- `output/resolved_tickets.json`, `output/audit_trail.json`, `output/design.md`.
