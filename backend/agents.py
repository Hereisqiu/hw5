"""Campus Customs agent team: five PydanticAI agents, fully connected through `delegate`.

Every shop fact and every write goes through the MCP server (mcp_server/server.py),
which works on data/campus_customs_new.db. There is no other shop-tools layer.
Each agent-loop step is appended to output/audit_trail.json.
"""

import asyncio
import json
import os
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from openai import AsyncOpenAI
from pydantic_ai import (
    Agent, CallToolsNode, ModelRequestNode, RetryPromptPart, RunContext, TextPart, ToolCallPart,
    ToolReturnPart, UsageLimits,
)
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

import audit
from models import AgentName, AgentReport, AuditRecord, BossDecision

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER = ROOT / "mcp_server" / "server.py"
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"

# Nearest .env wins: HW5/.env, then the course-root .env (load_dotenv never overrides).
for folder in [ROOT, *ROOT.parents]:
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env", override=False)

# The only model used by any agent. Not configurable on purpose.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- token controls (see output/harness.md) ----
TICKET_LIMITS = UsageLimits(          # shared by every agent working on one ticket
    request_limit=40,
    tool_calls_limit=60,
    total_tokens_limit=400_000,
)
MAX_DELEGATION_DEPTH = 2              # boss -> specialist -> one more specialist
MAX_DELEGATIONS_PER_TICKET = 8
MODEL_TIMEOUT_S = 120                 # one slow model call cannot stall the board
# No hidden reasoning, and a hard cap on output per call. With reasoning on, the model occasionally
# thought for minutes on a single step and the request timed out; each step here is a small, concrete job.
MODEL_SETTINGS = OpenAIResponsesModelSettings(openai_reasoning_effort="none", max_tokens=3000)

# Tools only a human may trigger (via the dashboard/backend). No agent ever sees them.
HUMAN_ONLY_TOOLS = {"approve_payment", "reject_payment"}

READ_BOARD = {"get_shop_date", "list_tickets", "list_approvals"}
ROLE_TOOLS: dict[str, set[str]] = {
    "boss": READ_BOARD | {"update_ticket", "get_cash_position", "list_invoices", "list_vendors", "list_drafts"},
    "inventory": READ_BOARD | {"check_stock", "check_bulk_order", "list_vendors", "list_invoices",
                               "get_invoice_status", "prepare_purchase_order"},
    "accounting": READ_BOARD | {"get_cash_position", "list_invoices", "get_invoice_status", "get_rent_due",
                                "check_bulk_order", "list_vendors", "prepare_payment", "prepare_purchase_order"},
    "facilities": READ_BOARD | {"get_rent_due", "get_cash_position", "prepare_payment"},
    "customer_service": READ_BOARD | {"check_stock", "check_bulk_order", "save_customer_draft", "list_drafts"},
}
assert not any(HUMAN_ONLY_TOOLS & tools for tools in ROLE_TOOLS.values())


def make_model() -> OpenAIResponsesModel:
    """gpt-6-luna through the Portkey gateway (Responses API: it supports tool calls with reasoning)."""
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set; add it to HW5/.env or the course-root .env")
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers={"x-portkey-api-key": key},
                         timeout=MODEL_TIMEOUT_S, max_retries=1)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


# One MCP connection (a stdio child process) shared by all agents.
mcp_toolset = MCPToolset(Client(StdioTransport(command=sys.executable, args=[str(MCP_SERVER)])))


@dataclass
class TeamDeps:
    run_id: str
    ticket_id: int | None
    chain: list[AgentName]
    delegations: list[int] = field(default_factory=lambda: [0])  # shared counter for the whole ticket
    # One delegation at a time per agent: parallel hand-offs from the same agent wait their turn.
    delegate_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def agent(self) -> AgentName:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


def _record(deps: TeamDeps, step: int, event: str, detail: dict, usage: RunUsage | None = None) -> None:
    audit.append(AuditRecord(
        timestamp=audit.now(), run_id=deps.run_id, ticket_id=deps.ticket_id, agent=deps.agent,
        depth=deps.depth, chain=list(deps.chain), step=step, event=event, detail=detail,
        usage={"requests": usage.requests, "tool_calls": usage.tool_calls, "input_tokens": usage.input_tokens,
               "output_tokens": usage.output_tokens, "total_tokens": usage.total_tokens} if usage else {},
    ))


async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> str:
    """Ask another team member to do a task in their area and return their report.

    Args:
        to: boss, inventory, accounting, facilities or customer_service.
        task: A specific, self-contained request including the ticket, SKU, size, qty, invoice or lease IDs they need.
    """
    deps = ctx.deps
    if to == deps.agent:
        return "You cannot delegate to yourself; do the task with your own tools."
    if to in deps.chain:
        return f"{to} already asked you for this (chain: {' -> '.join(deps.chain)}). Return your findings instead."
    if deps.depth >= MAX_DELEGATION_DEPTH:
        return f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached. Finish with what you have and note what is missing."
    async with deps.delegate_lock:
        if deps.delegations[0] >= MAX_DELEGATIONS_PER_TICKET:
            return f"Delegation budget ({MAX_DELEGATIONS_PER_TICKET} per ticket) used up. Finish with what you have."
        deps.delegations[0] += 1
        child = TeamDeps(run_id=deps.run_id, ticket_id=deps.ticket_id, chain=[*deps.chain, to], delegations=deps.delegations)
        _record(deps, 0, "delegate", {"to": to, "task": task}, ctx.usage)
        try:
            output = await run_agent(to, task, child, usage=ctx.usage)
        except UsageLimitExceeded:
            raise  # the whole ticket is out of budget
        except Exception as exc:  # one failed teammate should not sink the whole ticket
            return (f"{to} could not finish ({type(exc).__name__}: {exc}). "
                    "Continue with the facts you have and list this as an open issue.")
        return output.model_dump_json()


def _build_agent(name: AgentName) -> Agent:
    rules = (PROMPTS_DIR / "shop_rules.md").read_text()
    role = (PROMPTS_DIR / f"{name}.md").read_text()
    return Agent(
        make_model(),
        name=name,
        deps_type=TeamDeps,
        instructions=f"{role}\n\n{rules}",
        output_type=BossDecision if name == "boss" else AgentReport,
        tools=[delegate],
        model_settings=MODEL_SETTINGS,
        toolsets=[mcp_toolset.filtered(lambda ctx, tool, allowed=ROLE_TOOLS[name]: tool.name in allowed)],
        retries=2,
    )


AGENTS: dict[str, Agent] = {n: _build_agent(n) for n in ROLE_TOOLS}


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage | None = None):
    """Run one agent's loop step by step, auditing each step. Returns its structured output."""
    usage = usage if usage is not None else RunUsage()
    _record(deps, 0, "start", {"prompt": prompt}, usage)
    step = 0
    try:
        async with AGENTS[name].iter(prompt, deps=deps, usage=usage, usage_limits=TICKET_LIMITS) as run:
            async for node in run:
                if isinstance(node, CallToolsNode):
                    step += 1
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            _record(deps, step, "tool_call", {"tool": part.tool_name, "args": part.args_as_dict()}, usage)
                        elif isinstance(part, TextPart) and part.content.strip():
                            _record(deps, step, "model_response", {"text": part.content}, usage)
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            content = part.content if isinstance(part.content, str) else json.dumps(part.content, default=str)
                            _record(deps, step, "tool_result", {"tool": part.tool_name, "result": content}, usage)
                        elif isinstance(part, RetryPromptPart):
                            _record(deps, step, "retry", {"tool": part.tool_name, "message": str(part.content)}, usage)
            output = run.result.output
    except BaseException as exc:  # includes cancellation, so a stopped run never vanishes silently
        _record(deps, step, "error", {"type": type(exc).__name__, "message": str(exc) or repr(exc)}, usage)
        raise
    _record(deps, step, "finish", {"output": output.model_dump(mode="json")}, usage)
    return output


def reset_database() -> None:
    """Copy the original database over the working copy. Done before every full run."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


# Separate MCP connection for direct calls (reading the board, human approvals). Not given to any agent.
api_client = Client(StdioTransport(command=sys.executable, args=[str(MCP_SERVER)]))


async def call_mcp(tool: str, **args):
    """Call an MCP tool directly (used for reading the board and for human approvals)."""
    async with api_client:
        result = await api_client.call_tool(tool, args)
        return result.data if result.data is not None else result.structured_content


async def run_ticket(ticket_id: int, run_id: str | None = None) -> BossDecision:
    """The Boss works one ticket, delegating to the team as needed."""
    deps = TeamDeps(run_id=run_id or uuid.uuid4().hex[:12], ticket_id=ticket_id, chain=["boss"])
    prompt = (f"Handle ticket {ticket_id}. Read it from the board, coordinate the team, "
              "and make the final call. Consider the other open tickets that compete for the same cash or vendors.")
    async with mcp_toolset:
        return await run_agent("boss", prompt, deps)


async def run_board(reset: bool = True) -> list[BossDecision]:
    """Full run: reset the working database, then the Boss works every open ticket in order."""
    if reset:
        reset_database()
    run_id = uuid.uuid4().hex[:12]
    tickets = await call_mcp("list_tickets", status="open")
    decisions = []
    async with mcp_toolset:
        for t in tickets:
            decisions.append(await run_ticket(t["id"], run_id))
    return decisions
