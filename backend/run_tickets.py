"""Command-line runner for the agent team.

  python backend/run_tickets.py              # reset DB, then work every open ticket
  python backend/run_tickets.py --ticket 101 # work one ticket on the current DB (no reset)
"""

import argparse
import asyncio

from agents import run_board, run_ticket


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticket", type=int, help="Work a single ticket without resetting the database")
    args = parser.parse_args()
    decisions = [await run_ticket(args.ticket)] if args.ticket else await run_board(reset=True)
    for d in decisions:
        print(d.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
