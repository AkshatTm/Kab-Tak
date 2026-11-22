# Design brief (input for `/impeccable teach`)

Feed this to `/impeccable teach` so it can write `.impeccable.md`. After that, `.impeccable.md` is the design authority.

## Audience
- Students and self-learners who underestimate how long study and coding tasks take.
- Often working late at night (9 pm – 1 am). Many have time blindness / ADHD traits.
- Windows laptop users. Keyboard-heavy.

## Brand & tone
- Calm, honest, a bit warm. A good lab notebook, not a game.
- Never shaming: "This took 2.1× your guess" — not "You failed your estimate".
- Short sentences. Numbers first, explanation second.

## Visual direction
- **Dark mode default** (late-night use), light mode available.
- Low-saturation neutrals with **one accent colour** for the running timer and primary actions.
- A distinct but calm colour for "over estimate" — not alarm red.
- Clear numeric typography (tabular figures) for times and ratios.
- Density: compact; the chat and the current task should fit without scrolling on a 1366×768 laptop screen.

## Key screens
1. **Chat** (home) — message list, input box, task cards inline, running-task banner on top.
2. **Task card** — title, category chip, parts with quantities, my estimate, Confirm / Edit. After observation: prediction revealed *after* the estimate, with the last 5 similar tasks.
3. **Mini timer** — small always-on-top window: task title, elapsed vs my guess as a progress bar, pause/stop.
4. **Today** — tasks with guess, actual, ratio, outcome.
5. **Insights** — bias per category, gut-error trend, interval coverage.
6. **Plan check** — list in, realistic total + chance it fits + what to drop.
7. **Settings / onboarding** — API keys, categories, thresholds, export.

## Interaction principles
- Logging in seconds: Enter to confirm, single keys for Done/Partly/Stuck.
- Every number has a tooltip saying how it was computed.
- Empty states explain the observation period ("I'm learning how long your DSA work takes: 3 of 5 tasks").
- Accessible: WCAG AA contrast, keyboard reachable, no colour-only meaning.
