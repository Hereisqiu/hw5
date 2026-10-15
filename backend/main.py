"""Campus Customs operations API for the React dashboard.

Start from backend/:  uvicorn main:app --reload --port 8000

Every shop read and write goes through the MCP server (via agents.call_mcp or
the agents themselves). Payments only happen through the human approval route.
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import audit
from agents import api_client, call_mcp, mcp_toolset, reset_database, run_ticket

log = logging.getLogger("campus_customs.api")

# One agent run at a time: tickets share cash and vendors, so they are worked in sequence.
current_run: dict | None = None          # {"run_id", "ticket_id", "task"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep both MCP connections (agents' and the API's own) open while the API runs.
    async with mcp_toolset, api_client:
        yield


app = FastAPI(title="Campus Customs Operations", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # The Vite dev server (http://localhost:5173, or the next free port if that one is taken).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, **args):
    """Call an MCP tool; turn a tool-level {"error": ...} into a 400."""
    result = await call_mcp(tool, **args)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def _running() -> bool:
    return current_run is not None and not current_run["task"].done()


# ------------------------------------------------------------------ tickets


def _last_runs() -> dict[int, dict]:
    """Latest Boss run per ticket since the last reset, rebuilt from the audit trail."""
    runs: dict[int, dict] = {}
    for r in audit.read_all():
        if r["event"] == "reset":
            runs.clear()
        elif r["agent"] == "boss" and r["depth"] == 0 and r["ticket_id"] is not None:
            if r["event"] == "start":
                runs[r["ticket_id"]] = {"run_id": r["run_id"], "state": "running", "started_at": r["timestamp"]}
            elif r["event"] in ("finish", "error") and runs.get(r["ticket_id"], {}).get("run_id") == r["run_id"]:
                run = runs[r["ticket_id"]]
                run.update(state="done" if r["event"] == "finish" else "error", finished_at=r["timestamp"])
                if r["event"] == "finish":
                    run["decision"] = r["detail"]["output"]
                else:
                    run["error"] = r["detail"].get("message")
    return runs


@app.get("/api/tickets")
async def get_tickets():
    """All tickets with status, customer drafts, approvals and the latest agent run result."""
    tickets = await mcp("list_tickets", status=None)
    drafts = await mcp("list_drafts")
    approvals = await mcp("list_approvals", status=None)
    running_id = current_run["ticket_id"] if _running() else None
    last_runs = _last_runs()
    return [
        {
            **t,
            "running": t["id"] == running_id,
            "drafts": [d for d in drafts if d["ticket_id"] == t["id"]],
            "approvals": [a for a in approvals if a["ticket_id"] == t["id"]],
            # A ticket back at "open" was reset since its last run, so that run no longer applies.
            "last_run": None if t["status"] == "open" and t["id"] != running_id else last_runs.get(t["id"]),
        }
        for t in tickets
    ]


async def _run(ticket_id: int, run_id: str) -> None:
    try:
        await run_ticket(ticket_id, run_id)
    except BaseException:
        # run_agent already wrote the error to the audit trail; /api/tickets reports it.
        log.exception("Run %s for ticket %s stopped", run_id, ticket_id)


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket_route(ticket_id: int):
    """Start the agent team on one ticket. Returns at once; watch progress with /api/events."""
    global current_run
    if _running():
        raise HTTPException(409, f"Ticket {current_run['ticket_id']} is still running; wait for it to finish.")
    tickets = await mcp("list_tickets", status=None)
    if not any(t["id"] == ticket_id for t in tickets):
        raise HTTPException(404, f"Ticket {ticket_id} not found.")
    run_id = uuid.uuid4().hex[:12]
    current_run = {"run_id": run_id, "ticket_id": ticket_id, "task": asyncio.create_task(_run(ticket_id, run_id))}
    return {"run_id": run_id, "ticket_id": ticket_id, "state": "running"}


# ------------------------------------------------------------------ agent events


def _message(r: dict) -> str:
    """One readable line for the dashboard feed."""
    d = r["detail"]
    match r["event"]:
        case "start":
            return d.get("prompt", "")
        case "model_response":
            return d.get("text", "")
        case "tool_call":
            return f"{d['tool']}({json.dumps(d.get('args', {}))})"
        case "tool_result":
            return f"{d['tool']} → {d.get('result', '')}"
        case "delegate":
            return f"→ {d['to']}: {d['task']}"
        case "retry":
            return f"retry {d.get('tool') or ''}: {d.get('message', '')}"
        case "finish":
            out = d.get("output", {})
            return out.get("decision") or out.get("summary") or json.dumps(out)
        case "error":
            return f"{d.get('type')}: {d.get('message')}"
        case "human_decision":
            return f"{d['by']}: {d['action']}"
    return json.dumps(d)


@app.get("/api/events")
def get_events(since: int = 0, limit: int = 200, ticket_id: int | None = None, run_id: str | None = None):
    """Agent events after position `since` (poll with the returned `next`)."""
    records = audit.read_all()
    out = []
    for seq, r in enumerate(records[since:], start=since):
        if ticket_id is not None and r.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and r.get("run_id") != run_id:
            continue
        out.append({"seq": seq, **r, "message": _message(r)})
    out = out[-limit:]
    return {
        "events": out,
        "next": len(records),
        "running": {"run_id": current_run["run_id"], "ticket_id": current_run["ticket_id"]} if _running() else None,
    }


# ------------------------------------------------------------------ human approval


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving the payment.")


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.get("/api/approvals")
async def get_approvals(status: str | None = None):
    """Payments and purchase orders the agents prepared (pass status=pending for the queue)."""
    return await mcp("list_approvals", status=status)


async def _after_decision(ticket_id: int | None, status: str, note: str, who: str) -> None:
    """Once a waiting ticket has no pending approvals left, move it on and note the human's decision."""
    if ticket_id is None:
        return
    tickets = await mcp("list_tickets", status="waiting_approval")
    pending = await mcp("list_approvals", status="pending")
    if any(t["id"] == ticket_id for t in tickets) and not any(a["ticket_id"] == ticket_id for a in pending):
        await mcp("update_ticket", ticket_id=ticket_id, status=status, note=note, author=f"human:{who}")


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: ApproveBody):
    """A human approves a prepared payment or purchase order; this executes it and updates cash."""
    result = await mcp("approve_payment", approval_id=approval_id, approved_by=body.approved_by)
    audit.append_human(f"approve #{approval_id}", body.approved_by, result)
    a = result["approval"]
    await _after_decision(a["ticket_id"], "resolved", f"Approval #{approval_id} paid. {a['decision_note']}",
                          body.approved_by)
    return result


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: RejectBody):
    """A human rejects a prepared payment or purchase order. No money moves."""
    result = await mcp("reject_payment", approval_id=approval_id, rejected_by=body.rejected_by, reason=body.reason)
    audit.append_human(f"reject #{approval_id}", body.rejected_by, result)
    await _after_decision(result["ticket_id"], "in_progress", f"Approval #{approval_id} rejected: {body.reason}",
                          body.rejected_by)
    return result


# ------------------------------------------------------------------ cash and reset


@app.get("/api/cash")
async def get_cash():
    """Checking balance from cash_accounts, plus money queued for approval and payments made."""
    pos = await mcp("get_cash_position")
    checking = next((a for a in pos["accounts"] if a["account"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account.")
    return {"today": pos["today"], "checking": checking, "payments": pos["payments"]}


@app.post("/api/reset")
async def reset():
    """Copy data/campus_customs.db over the working copy. The audit trail is kept."""
    if _running():
        raise HTTPException(409, "An agent run is in progress; wait for it to finish before resetting.")
    reset_database()
    audit.append_reset()
    return {"reset": True, "cash": await get_cash()}
