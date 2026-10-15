"""Pydantic types shared by the agent team, the audit trail and the API."""

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved"]


class AgentReport(BaseModel):
    """What a specialist (or any delegated agent) hands back to whoever asked."""

    summary: str = Field(description="Two or three sentences answering the task you were given.")
    facts: list[str] = Field(
        default_factory=list,
        description="Verified facts from MCP tool results, each with its number/date, e.g. 'Invoice 501: $840 open, due 2026-08-28'.",
    )
    actions_taken: list[str] = Field(
        default_factory=list, description="Writes you made through tools (approvals queued, drafts saved). Empty if none."
    )
    approval_ids: list[int] = Field(default_factory=list, description="IDs of approvals you queued for a human.")
    draft_ids: list[int] = Field(default_factory=list, description="IDs of customer drafts you saved.")
    blockers: list[str] = Field(default_factory=list, description="Anything stopping the work, with the reason.")
    recommendation: str = Field(description="What you think should happen next, and who should do it.")


class BossDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    status: TicketStatus = Field(description="Status you set on the ticket with update_ticket.")
    decision: str = Field(description="The final call in plain words, including any discount decided.")
    agents_involved: list[AgentName] = Field(default_factory=list)
    approval_ids: list[int] = Field(default_factory=list, description="Approvals waiting on a human for this ticket.")
    draft_ids: list[int] = Field(default_factory=list, description="Customer drafts saved for this ticket.")
    depends_on: list[str] = Field(
        default_factory=list, description="Other tickets, invoices or payments this ticket depends on, and why."
    )
    open_issues: list[str] = Field(default_factory=list, description="What is still unresolved and who owns it.")


class AuditRecord(BaseModel):
    """One line of output/audit_trail.json: a single step of one agent's loop."""

    timestamp: str
    run_id: str
    ticket_id: int | None
    agent: AgentName | Literal["human"]
    depth: int = Field(description="0 for the Boss's top-level run, +1 for each delegation.")
    chain: list[AgentName] = Field(description="Who delegated to whom to reach this agent.")
    step: int
    event: Literal[
        "start", "model_response", "tool_call", "tool_result", "retry", "delegate", "finish", "error",
        "human_decision", "reset"
    ]
    detail: dict[str, Any]
    usage: dict[str, int] = Field(default_factory=dict, description="Cumulative tokens/requests for this ticket so far.")
