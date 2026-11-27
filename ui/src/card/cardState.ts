import type { TaskCreate } from '../api/client'

/** A task card is the body of POST /api/tasks while the user is still editing it. */
export type Card = TaskCreate

const MAX_ESTIMATE_MIN = 10_000 // same limits as backend/app/timer/inputs.py
const MAX_QTY = 100_000

export function fromCard(card: Card): Card {
  return { ...card, parts: card.parts.map((p) => ({ ...p })) }
}

export function toTaskCreate(card: Card): Card {
  return { ...card, title: card.title.trim() }
}

export function isEdited(original: Card, current: Card): boolean {
  return JSON.stringify(toTaskCreate(original)) !== JSON.stringify(toTaskCreate(current))
}

/** Why the card cannot be confirmed yet, or null when it can. */
export function blocker(card: Card): string | null {
  const guess = card.estimate_min
  if (!card.title.trim()) return 'Add a title to confirm.'
  if (guess == null || guess <= 0) return 'Add your guess in minutes to confirm.'
  if (!Number.isInteger(guess)) return 'Use whole minutes for your guess.'
  if (guess > MAX_ESTIMATE_MIN) return `A guess can be at most ${MAX_ESTIMATE_MIN} minutes.`
  if (!card.parts.every((p) => p.planned_qty > 0 && p.planned_qty <= MAX_QTY)) {
    return 'Give every part a quantity above 0.'
  }
  return null
}

export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (!h) return `${m} min`
  return m ? `${h} h ${m} min` : `${h} h`
}
