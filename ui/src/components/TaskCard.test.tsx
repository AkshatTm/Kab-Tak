import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CARD, CATEGORIES, PART_TYPES, fakeBackend } from '../testApi'
import TaskCard from './TaskCard'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function show(estimate: number | null = null) {
  const onSaved = vi.fn()
  render(
    <TaskCard
      card={{ ...CARD, estimate_min: estimate }}
      parseJson={{ intent: 'create_task' }}
      categories={CATEGORIES}
      partTypes={PART_TYPES}
      onSaved={onSaved}
    />,
  )
  return { onSaved }
}

const guess = () => screen.getByLabelText(/your guess/i)
const confirm = () => screen.getByRole('button', { name: /confirm/i })
const enter = () => fireEvent.submit(guess().closest('form')!)

it('cannot be confirmed without a guess, and says why', () => {
  fakeBackend()
  show()
  expect(confirm()).toBeDisabled()
  expect(confirm()).toHaveAccessibleDescription(/add your guess/i)
  expect(guess()).toHaveFocus()
})

it('typing a guess enables Confirm and submitting saves the edited card', async () => {
  const api = fakeBackend()
  const { onSaved } = show()
  fireEvent.change(guess(), { target: { value: '40' } })
  fireEvent.change(screen.getByLabelText(/quantity/i), { target: { value: '3' } })
  expect(confirm()).toBeEnabled()
  expect(screen.getByText('40 min')).toBeInTheDocument()
  enter()
  expect(await screen.findByText(/^Saved/)).toBeInTheDocument()
  const [task] = api.posts('POST /api/tasks')
  expect(task.body).toEqual({
    ...CARD,
    estimate_min: 40,
    parts: [{ part_type_id: 'pt-practice', planned_qty: 3 }],
  })
  expect(onSaved).toHaveBeenCalledOnce()
})

it('records one correction for an edited card', async () => {
  const api = fakeBackend()
  show()
  fireEvent.change(guess(), { target: { value: '40' } })
  enter()
  await screen.findByText(/^Saved/)
  const corrections = api.posts('POST /api/corrections')
  expect(corrections).toHaveLength(1)
  expect(corrections[0].body).toEqual({
    raw_text: CARD.raw_text,
    llm_output_json: { intent: 'create_task' },
    corrected_json: { ...CARD, estimate_min: 40 },
  })
})

it('records no correction for an untouched card', async () => {
  const api = fakeBackend()
  show(30)
  enter()
  await screen.findByText(/^Saved/)
  expect(api.posts('POST /api/corrections')).toHaveLength(0)
})

it('saves once even if submitted twice', async () => {
  const api = fakeBackend()
  show(30)
  enter()
  enter()
  await screen.findByText(/^Saved/)
  expect(api.posts('POST /api/tasks')).toHaveLength(1)
})

it.each([409, 422])('keeps the card and says what failed on %i', async (status) => {
  fakeBackend({
    'POST /api/tasks': () => Response.json({ detail: [{ msg: 'title is too odd' }] }, { status }),
  })
  show(30)
  enter()
  expect(await screen.findByRole('alert')).toHaveTextContent(/title is too odd/)
  expect(guess()).toHaveValue(30)
  expect(confirm()).toBeEnabled()
})

it('still reports the task saved when only the correction fails', async () => {
  fakeBackend({ 'POST /api/corrections': () => new Response('x', { status: 500 }) })
  show()
  fireEvent.change(guess(), { target: { value: '40' } })
  enter()
  await waitFor(() => expect(screen.getByText(/^Saved/)).toBeInTheDocument())
  expect(screen.getByText(/^Saved/)).toHaveTextContent(/fix wasn't recorded/i)
})

it('adds and removes parts', async () => {
  const api = fakeBackend()
  show(30)
  fireEvent.click(screen.getByRole('button', { name: /remove practice problems/i }))
  fireEvent.click(screen.getByRole('button', { name: /add part/i }))
  fireEvent.change(screen.getByLabelText(/part type/i), { target: { value: 'pt-other' } })
  enter()
  await screen.findByText(/^Saved/)
  expect(api.posts('POST /api/tasks')[0].body).toMatchObject({
    parts: [{ part_type_id: 'pt-other', planned_qty: 1 }],
  })
})

it('cannot be edited while it is being saved', async () => {
  fakeBackend()
  show(30)
  enter()
  expect(guess()).toBeDisabled()
  expect(screen.getByLabelText(/title/i)).toBeDisabled()
  await screen.findByText(/^Saved/)
})

// a focused number box changes its value on mouse wheel: scrolling must not rewrite a guess
it.each([/your guess/i, /quantity/i])('lets go of %s when the wheel turns over it', (label) => {
  fakeBackend()
  show(30)
  const box = screen.getByLabelText(label)
  box.focus()
  fireEvent.wheel(box)
  expect(box).not.toHaveFocus()
})

it('keeps keyboard focus in the card when a part is removed', () => {
  fakeBackend()
  show(30)
  fireEvent.click(screen.getByRole('button', { name: /remove practice problems/i }))
  expect(screen.getByRole('button', { name: /add part/i })).toHaveFocus()
})

it('returns focus to the guess when saving fails', async () => {
  fakeBackend({ 'POST /api/tasks': () => new Response('x', { status: 500 }) })
  show(30)
  // a real browser drops focus from a control that gets disabled; jsdom keeps it, so drop it first
  guess().blur()
  enter()
  await screen.findByRole('alert')
  expect(guess()).toHaveFocus()
})
