# Research basis (why the design looks like this)

Read this once for context. SPEC.md is the authority if anything conflicts.

## 1. Evidence-Based Scheduling (Joel Spolsky, 2007)
- velocity = estimate ÷ actual, tracked per person.
- Most estimators get the **scale** wrong but the **relative** sizes right → model the error as a
  multiplier, i.e. in **log space** (`r = ln(actual/estimate)`).
- Don't add estimates; run a **Monte Carlo** over historical errors and report a probability distribution.
  → used in Plan check.
- https://www.joelonsoftware.com/2007/10/26/evidence-based-scheduling/

## 2. Planning fallacy and the outside view
- People underestimate their own task times (Kahneman & Tversky; Buehler, Griffin & Ross 1994).
- Fix: **reference class forecasting** — compare the task to a class of similar past tasks
  (Lovallo & Kahneman 2003; Flyvbjerg 2008).
- Experimental work (Lorko et al.) found extra information alone didn't raise people's confidence calibration
  → history must be **shown at the moment of estimating** (last 5 similar tasks), not hidden in reports.

## 3. Segmentation / unpacking
- Time allocated to a whole task is smaller than the sum allocated to its subtasks (Forsyth & Burt 2008).
- Unpacking effects depend on which components are listed (Hadjichristidis et al.).
- → Tasks are stored with **parts and quantities**, enabling Level B content rates and Phase 2 tiny steps.

## 4. Time-blindness app patterns
- When the estimate runs out, ask whether the user finished and keep counting → **overrun check-in**.
- Forgotten running timers are the biggest data-quality problem; Toggl/Clockify solve it with idle
  detection (keep / discard / split) → **F6 recovery + F16 idle**.

## 5. Statistics choices
- **Shrinkage (empirical Bayes):** small categories borrow strength from the global bias.
- **Recency weighting:** lets improvement show up instead of being averaged away.
- **Censoring:** "stuck/gave up" durations are lower bounds → excluded from fitting in Phase 1.
- **Non-negative least squares** for per-part rates from task totals.
- **Walk-forward evaluation** to avoid leakage; store predictions as made.
- **Conformal prediction (MAPIE)** is a later upgrade for intervals with coverage guarantees.

## 6. LLM use
- The LLM only turns chat into structured JSON (classification + extraction), validated by Pydantic.
- Free tiers (Groq, Cerebras, Gemini AI Studio) are OpenAI-compatible → one client, fallback chain.
- Free-tier limits and model lists change: always read current provider docs before hardcoding model ids.
