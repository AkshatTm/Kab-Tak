import { useId, useRef, useState, type FormEvent } from 'react'
import { createTask, postCorrection, type Category, type PartType } from '../api/client'
import { blocker, formatMinutes, fromCard, isEdited, toTaskCreate, type Card } from '../card/cardState'

type Props = {
  card: Card
  parseJson: Record<string, unknown> | null
  categories: Category[]
  partTypes: PartType[]
  autoFocus?: boolean
  onSaved: () => void
}

export default function TaskCard(props: Props) {
  const { card, parseJson, categories, partTypes, autoFocus = true, onSaved } = props
  const [draft, setDraft] = useState(() => fromCard(card))
  const [phase, setPhase] = useState<'editing' | 'saving' | 'saved'>('editing')
  const [problem, setProblem] = useState<string | null>(null)
  const [correctionLost, setCorrectionLost] = useState(false)
  const busy = useRef(false)
  const reasonId = useId()

  const change = (patch: Partial<Card>) => setDraft((d) => ({ ...d, ...patch }))
  const changePart = (index: number, patch: Partial<Card['parts'][number]>) =>
    change({ parts: draft.parts.map((p, i) => (i === index ? { ...p, ...patch } : p)) })
  const typeOf = (id: string) => partTypes.find((t) => t.id === id)
  const reason = blocker(draft)
  const guess = draft.estimate_min

  async function confirm(event: FormEvent) {
    event.preventDefault()
    if (busy.current || reason) return
    busy.current = true
    setPhase('saving')
    setProblem(null)
    try {
      await createTask(toTaskCreate(draft))
    } catch (error) {
      busy.current = false
      setPhase('editing')
      setProblem(`Couldn't save: ${(error as Error).message}. Your card is unchanged.`)
      return
    }
    if (card.raw_text && isEdited(card, draft)) {
      try {
        await postCorrection({
          raw_text: card.raw_text,
          llm_output_json: parseJson,
          corrected_json: toTaskCreate(draft),
        })
      } catch {
        setCorrectionLost(true) // the task is saved; only the learning example is missing
      }
    }
    setPhase('saved')
    onSaved()
  }

  if (phase === 'saved') {
    return (
      <p role="status" className="rounded-lg border border-line px-4 py-3">
        Saved “{draft.title.trim()}”. Your guess: <strong>{formatMinutes(guess!)}</strong>.
        {correctionLost && ' Your fix wasn\'t recorded for next time.'}
      </p>
    )
  }

  return (
    <form
      aria-label="Task card"
      noValidate
      onSubmit={confirm}
      className="grid gap-2.5 rounded-lg border border-line bg-surface p-3"
    >
      <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
        <label className="grid flex-1 basis-56 gap-1 text-sm text-dim">
          Title
          <input
            className="field text-base font-semibold text-ink"
            value={draft.title}
            onChange={(e) => change({ title: e.target.value })}
          />
        </label>
        <label className="grid gap-1 text-sm text-dim">
          Category
          <select
            className="field h-[2.4rem] text-base text-ink"
            value={draft.category_id ?? ''}
            onChange={(e) => change({ category_id: e.target.value || null })}
          >
            <option value="">No category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 py-2">
          <input
            type="checkbox"
            className="size-4 accent-accent"
            checked={draft.tentative}
            onChange={(e) => change({ tentative: e.target.checked })}
          />
          Maybe (tentative)
        </label>
      </div>

      <fieldset className="grid gap-1.5">
        <legend className="mb-1 text-sm text-dim">Parts</legend>
        {draft.parts.map((part, i) => {
          const label = typeOf(part.part_type_id)?.label ?? 'part'
          return (
            // rows have no id of their own; every field is controlled, so index keys are safe
            <div
              key={i}
              className="grid grid-cols-[minmax(0,15rem)_4.5rem_4.5rem_auto] items-center gap-2 text-sm"
            >
              <select
                aria-label="Part type"
                className="field py-1"
                value={part.part_type_id}
                onChange={(e) => changePart(i, { part_type_id: e.target.value })}
              >
                {partTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="0"
                step="any"
                aria-label={`Quantity of ${label}`}
                className="field py-1 text-right"
                value={Number.isNaN(part.planned_qty) ? '' : part.planned_qty}
                onChange={(e) => changePart(i, { planned_qty: e.target.valueAsNumber })}
              />
              <span className="text-dim">
                {typeOf(part.part_type_id)?.unit.replace('content_min', 'video min')}
              </span>
              <button
                type="button"
                aria-label={`Remove ${label}`}
                title="Remove"
                className="btn justify-self-start p-1.5"
                onClick={() => change({ parts: draft.parts.filter((_, j) => j !== i) })}
              >
                <svg aria-hidden viewBox="0 0 16 16" className="size-4" stroke="currentColor">
                  <path d="M4 4l8 8M12 4l-8 8" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          )
        })}
        <button
          type="button"
          className="btn justify-self-start py-1 text-sm"
          onClick={() => {
            const type = partTypes.find((t) => t.key === 'other') ?? partTypes[0]
            change({ parts: [...draft.parts, { part_type_id: type.id, planned_qty: 1 }] })
          }}
        >
          Add part
        </button>
      </fieldset>

      <div className="flex flex-wrap items-end gap-x-3 gap-y-1 border-t border-line pt-2">
        <label className="grid gap-1 text-sm text-dim">
          Your guess (minutes)
          <input
            type="number"
            inputMode="numeric"
            min="1"
            autoFocus={autoFocus}
            className="field w-32 py-0.5 text-3xl font-semibold text-ink"
            value={guess ?? ''}
            onChange={(e) =>
              change({ estimate_min: e.target.value === '' ? null : e.target.valueAsNumber })
            }
          />
        </label>
        <span className="pb-2 text-dim">
          {guess != null && Number.isInteger(guess) && guess > 0 ? formatMinutes(guess) : ''}
        </span>
        <p id={reasonId} className="ml-auto pb-2 text-sm text-dim">
          {reason ?? 'Press Enter to confirm.'}
        </p>
        <button
          type="submit"
          className="btn btn-primary mb-1"
          disabled={phase === 'saving' || reason !== null}
          aria-describedby={reasonId}
        >
          {phase === 'saving' ? 'Saving…' : 'Confirm task'}
        </button>
      </div>
      {problem && (
        <p role="alert" className="text-error">
          {problem}
        </p>
      )}
    </form>
  )
}
