import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'
import { fakeBackend } from './testApi'

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('shows the chat with a connected chip when the backend answers', async () => {
  fakeBackend()
  renderApp()
  expect(screen.getByText(/connecting/i)).toBeInTheDocument()
  expect(await screen.findByText('Connected')).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: /message/i })).toBeInTheDocument()
})

it('shows an error when the backend is unreachable', async () => {
  fakeBackend({ 'GET /api/health': () => new Response('nope', { status: 401 }) })
  renderApp()
  expect(await screen.findByText(/backend unreachable/i)).toBeInTheDocument()
})
