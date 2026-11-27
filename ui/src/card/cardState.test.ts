import { describe, expect, it } from 'vitest'
import { blocker, formatMinutes, fromCard, isEdited, toTaskCreate, type Card } from './cardState'

const card: Card = {
  title: 'Graph problems',
  raw_text: '2 graph problems, 40 min',
  category_id: 'cat-dsa',
  estimate_min: 40,
  tentative: false,
  familiarity: null,
  source: 'chat',
  parts: [{ part_type_id: 'pt-practice', planned_qty: 2 }],
}

describe('blocker', () => {
  it('is null for a complete card', () => expect(blocker(card)).toBeNull())

  it.each([
    [{ estimate_min: null }, /guess/i],
    [{ estimate_min: 0 }, /guess/i],
    [{ estimate_min: 1.5 }, /whole minutes/i],
    [{ estimate_min: 10_001 }, /10000/],
    [{ title: '   ' }, /title/i],
    [{ parts: [{ part_type_id: 'pt-practice', planned_qty: NaN }] }, /quantity/i],
    [{ parts: [{ part_type_id: 'pt-practice', planned_qty: 0 }] }, /quantity/i],
  ])('names what is missing for %j', (patch, reason) => {
    expect(blocker({ ...card, ...patch })).toMatch(reason)
  })
})

describe('isEdited', () => {
  it('is false for an untouched card', () => expect(isEdited(card, fromCard(card))).toBe(false))

  it.each([
    { title: 'Other' },
    { category_id: null },
    { estimate_min: 45 },
    { tentative: true },
    { parts: [] },
    { parts: [{ part_type_id: 'pt-practice', planned_qty: 3 }] },
  ])('is true after %j', (patch) => {
    expect(isEdited(card, { ...fromCard(card), ...patch })).toBe(true)
  })

  it('ignores surrounding spaces in the title', () => {
    expect(isEdited(card, { ...card, title: ' Graph problems ' })).toBe(false)
  })
})

it('fromCard copies parts so edits never touch the original', () => {
  const copy = fromCard(card)
  copy.parts![0].planned_qty = 9
  expect(card.parts![0].planned_qty).toBe(2)
})

it('toTaskCreate is the card with a trimmed title', () => {
  expect(toTaskCreate({ ...card, title: '  Graphs ' })).toEqual({ ...card, title: 'Graphs' })
})

it.each([
  [45, '45 min'],
  [60, '1 h'],
  [90, '1 h 30 min'],
])('formats %i minutes', (min, shown) => expect(formatMinutes(min)).toBe(shown))
