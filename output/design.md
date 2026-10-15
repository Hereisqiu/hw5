# Campus Customs Ops Floor: dashboard design

The dashboard (`frontend/`, React + Vite + TypeScript) is the human's seat on the shop's operations floor. You can watch the five agents work a ticket, see who handed what to whom, and approve the money they ask for. It talks to the FastAPI backend at `http://localhost:8000` and starts with `npm run dev` in `frontend/`.

## Layout

The screen has a top bar over three columns, arranged around one question: *what is the crew doing, and what do they need from me?*

```
┌────────────────────────────────────────────────────────────────────────┐
│ crew badges · Campus Customs Ops Floor · 1/3 resolved   [ Checking $ ] [Reset] │
├──────────────┬───────────────────────────────────┬─────────────────────┤
│ Ticket board │ Ticket header   (state pill)       │ Approvals │ Summary │ Drafts │
│  #101 card   │ ┌───────── Crew map ──────────┐    │                     │
│  #102 card   │ │  5 critters, live edges      │    │  approval cards     │
│  #103 card   │ └──────────────────────────────┘    │  or agent summary   │
│              │ ┌───────── Live feed ──────────┐    │  or draft postcards │
│              │ │ bubbles · hand-offs · tools  │    │                     │
│              │ └──────────────────────────────┘    │  colour legend      │
└──────────────┴───────────────────────────────────┴─────────────────────┘
```

- **Left, the ticket board.** One card per ticket: type glyph, number, subject, requester, the item or lease, status chips, and one button. The button reads *Send the crew*, *Running…*, or *Run again*. Clicking a card selects it, and every other panel follows the selection.
- **Center, the floor.** A header shows the ticket and a state pill (*Waiting for the crew*, *Crew at work*, *Resolved*). Under it are the **crew map** and the **live feed**. You watch the work where the work happens.
- **Right, the human's desk.** Three tabs:
  - **Approvals** has a pink badge counting pending items.
  - **Crew summary** shows what each agent did on this ticket.
  - **Drafts** holds customer messages, which are never sent.

  A colour legend sits at the bottom.
- **Top bar.** Shows the crew, the resolved count, the shop date, the **cash meter**, and a two-click **Reset shop** button (the first click turns red and asks you to click again).

Below 1150 px wide, the right column drops under the other two so the dashboard still works on a laptop split screen.

## How agents are distinguished

Each agent has three things that always go together: a **colour**, a **CSS-drawn critter**, and a **name**.

| Agent | Colour | Critter accessory |
|---|---|---|
| Boss | hot pink `#ff4fa3` | gold crown |
| Inventory | mint `#4fe3b0` | little cardboard-box hat |
| Accounting | gold `#ffd166` | round glasses |
| Facilities | sky blue `#5cc8ff` | yellow hard hat |
| Customer Service | lilac `#b78cff` | headset with mic |
| You (human) | white | pink heart |

**The critters.** They're built entirely in HTML/CSS (`Critter.tsx` plus `.critter-*` styles), with no images. Each is a rounded body with eyes, highlights, blush and a mouth, and the accessory is drawn with `clip-path`, gradients and borders. Their mood follows the run:
- **Busy:** hops while working.
- **Happy:** bigger smile once it has taken part.
- **Sleepy:** half-closed eyes and faded colour when it isn't involved.
- **Idle:** blinks every few seconds.

**The colour shows up everywhere an agent appears:**
- the left border and name of its chat bubbles;
- the name of every tool chip it runs;
- its node and label on the crew map;
- its row in the crew summary;
- the gradient text on hand-off cards (Boss pink fading into Inventory mint, for example).

**Indentation shows delegation depth.** A Boss → Inventory → Accounting chain steps visibly to the right in the feed. Each hand-off is a dashed card naming who asked whom and what the task was.

## The live feed

- **Bubbles** hold what an agent says. A finished agent's bubble becomes a **report card** with its summary, verified facts, recommendation and open issues. The Boss's final card is labelled *Final call*.
- **Tool chips** are compact monospace pills showing each MCP call and its key arguments, marked *done* or *refused*. Clicking a chip opens the exact arguments and the raw tool result, so every claim can be checked against the data the agent saw.
- **A typing indicator** shows the critter of the agent working right now ("Accounting is working…"), so it's always clear who has the ticket.
- **Human decisions** (approve or reject) appear as right-aligned bubbles from *You*, in the same timeline.
- The feed scrolls to new events automatically, unless you have scrolled up to read.

It polls `/api/events` every 1.2 s while a run is active and every 3.5 s otherwise.

## The crew map

The five critters sit on a pentagon with the Boss at the top. Faint dotted lines join every pair, because the team is fully connected and anyone can delegate to anyone. When an agent delegates during the run, that edge becomes a **glowing pink line with flowing dashes**, and it gets thicker if the hand-off happens more than once. The active agent gets a soft halo in its own colour. At a glance you can see a ticket's real path, for example Boss → Inventory → Accounting, then Boss → Customer Service.

## Resolved tickets

- When a ticket's run finishes, its card gets a pink **RESOLVED** rubber stamp. The stamp lands with a small "thunk" animation, tilted like a real stamp. The card background warms to a pink-tinted gradient, and the header pill switches to a green *Resolved*.
- The database status stays visible as a chip next to the stamp: *Awaiting approval*, or *Resolved* once a human approves the last payment. That way you can tell "the crew is done" apart from "the shop is done".
- A *1 to approve* chip pulses pink until you deal with it.
- The top bar counts resolved tickets (*2/3 tickets resolved*).
- A run that fails shows a short red line on the card, and the ticket stays runnable.
- A reset clears the stamps. The board shows the stamp only for runs since the last reset, and that state is rebuilt from the audit trail, so it survives a backend restart.

## Cash balance

The **cash meter** in the top bar is the one number that always stays in view.
- **Big balance.** The checking balance from `cash_accounts`, in heavy tabular numerals. After an approved payment it **counts down** smoothly to the new value, and the meter **flashes pink**.
- **Bar.** Pink shows the cash left after every pending approval. Striped gold shows money queued but not yet approved.
- **Status line.** Reads *"$3,240.00 queued · $160.00 after approvals"*, or turns gold with *"short by $…"* when queued payments exceed the cash, which is exactly the squeeze between tickets 101–103.
- **Ledger.** Clicking the meter opens a ledger of every payment out, with who approved it. Cash only goes out in this shop.

Each approval card repeats the key number, *Balance after: $2,560.00*. If a payment would overdraw the account, the card turns red and warns that it will be refused, before you click.

## Human approval

Approvals are deliberately physical:
- Type your name once in *Approving as*. It's saved in the browser and recorded as `approved_by`.
- Each card shows what is being paid, the amount in large pink type, which agent asked and why, and the balance afterwards.
- **Approve & pay** is the only button in the whole UI that moves money.
- **Reject** asks for a reason first.
- A toast confirms the result ("Paid $840.00. Checking is now $2,560.00.") or shows the backend's refusal in red.

## Creative details

- **The crew in the logo.** The five critters sit in a pill next to the title and hop together whenever a run is in progress.
- **Draft postcards.** Customer drafts are shown as slightly tilted cream postcards with a pink top edge and a dashed **DRAFT · NOT SENT** stamp. It's a playful reminder that nothing leaves the shop.
- **Feel and motion:**
  - Bubbles and cards rise in as they arrive.
  - The running ticket card has a marching pink stripe across its top.
  - Buttons press in slightly when clicked.
  - All motion switches off for users who prefer reduced motion.
- **Black and pink throughout.** The page is near-black with soft pink glows in the corners, pink as the action colour, and the five agent colours as the only other accents. Status colours (mint for good, gold for waiting, red for refused) are used sparingly so they stand out.
- **Clear empty states.** A sleepy Boss critter waits in an empty feed ("Press *Send the crew*…"). An empty approvals tab explains "Agents can only prepare them, and you pay." A red banner appears if the backend at `localhost:8000` can't be reached.
