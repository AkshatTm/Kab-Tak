import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { CARD, fakeBackend } from '../testApi'
import ChatScreen from './ChatScreen'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <ChatScreen />
    </QueryClientProvider>,
  )
}

const box = () => screen.getByRole('textbox', { name: /message/i })
function send(text: string) {
  fireEvent.change(box(), { target: { value: text } })
  fireEvent.keyDown(box(), { key: 'Enter' })
}
const answer = (over: object) => () =>
  Response.json({
    intent: 'create_task',
    reply: 'Check the card, then confirm.',
    cards: [CARD],
    parsed: true,
    parse_json: {},
    ...over,
  })

it('shows the message, then the card, and sends the token header', async () => {
  const api = fakeBackend({ 'POST /api/chat': answer({}) })
  show()
  send('  2 graph problems  ')
  expect(screen.getByText('2 graph problems')).toBeInTheDocument()
  expect(await screen.findByDisplayValue('Graph problems')).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Check the card, then confirm.')
  expect(box()).toHaveValue('')
  const [chat] = api.posts('POST /api/chat')
  expect(chat.body).toEqual({ text: '2 graph problems' })
  expect(chat.token).not.toBeNull()
})

it('shows an editable empty card when parsing failed', async () => {
  const empty = { ...CARD, title: 'blah', category_id: null, parts: [] }
  fakeBackend({
    'POST /api/chat': answer({
      intent: 'unknown',
      reply: "Couldn't understand that — fill the card manually",
      cards: [empty],
      parsed: false,
      parse_json: null,
    }),
  })
  show()
  send('blah')
  expect(await screen.findByLabelText(/title/i)).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent(/fill the card manually/)
  expect(screen.getByLabelText(/title/i)).toHaveValue('blah')
  expect(screen.getByLabelText(/your guess/i)).toHaveValue(null)
})

it('shows a text reply with no card for a question', async () => {
  fakeBackend({
    'POST /api/chat': answer({ intent: 'question', reply: 'Tell me the task.', cards: [] }),
  })
  show()
  send('what can you do?')
  await screen.findAllByText('Tell me the task.')
  expect(screen.getByRole('status')).toHaveTextContent('Tell me the task.')
  expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument()
})

it('does not send on Shift+Enter or when empty', () => {
  const api = fakeBackend()
  show()
  send('   ')
  fireEvent.change(box(), { target: { value: 'two\nlines' } })
  fireEvent.keyDown(box(), { key: 'Enter', shiftKey: true })
  expect(api.posts('POST /api/chat')).toHaveLength(0)
})

it('gives the text back when the backend cannot be reached', async () => {
  fakeBackend({ 'POST /api/chat': () => new Response('down', { status: 500 }) })
  show()
  send('2 graph problems')
  expect(await screen.findByRole('alert')).toHaveTextContent(/couldn't send/i)
  expect(box()).toHaveValue('2 graph problems')
})

it('does not pull focus away from a message being typed', async () => {
  fakeBackend({ 'POST /api/chat': answer({}) })
  show()
  box().focus()
  send('2 graph problems')
  fireEvent.change(box(), { target: { value: 'next one, 20' } })
  await screen.findByLabelText(/your guess/i)
  expect(box()).toHaveFocus()
})

it('keeps both messages when a send fails after more typing', async () => {
  fakeBackend({ 'POST /api/chat': () => new Response('down', { status: 500 }) })
  show()
  send('first task')
  fireEvent.change(box(), { target: { value: 'second task' } })
  await screen.findByRole('alert')
  expect(box()).toHaveValue('first task\nsecond task')
})

it('moves focus to the next unsaved card, then back to the message box', async () => {
  const ready = { ...CARD, estimate_min: 30 }
  fakeBackend({
    'POST /api/chat': answer({ cards: [ready, { ...ready, title: 'Second' }] }),
  })
  show()
  send('two things')
  const [first, second] = await screen.findAllByLabelText(/your guess/i)
  expect(first).toHaveFocus()
  fireEvent.submit(first.closest('form')!)
  await screen.findByText(/^Saved “Graph problems”/, { selector: 'p:not([role])' })
  expect(second).toHaveFocus()
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/saved/i))
  fireEvent.submit(second.closest('form')!)
  await screen.findByText(/^Saved “Second”/, { selector: 'p:not([role])' })
  expect(box()).toHaveFocus()
})

it('announces through one live region, not the whole conversation', () => {
  fakeBackend()
  show()
  expect(screen.getByRole('list', { name: 'Conversation' })).not.toHaveAttribute('aria-live')
  expect(screen.getByRole('status')).toBeInTheDocument()
})
