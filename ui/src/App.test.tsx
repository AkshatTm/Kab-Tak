import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

it('shows health status when the backend answers', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => Response.json({ status: 'ok', version: '0.1.0', db: 'ok' })),
  )
  renderApp()
  expect(screen.getByText(/connecting/i)).toBeInTheDocument()
  expect(await screen.findByText(/Backend: ok · db ok · v0\.1\.0/)).toBeInTheDocument()
})

it('shows an error when the backend is unreachable', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response('nope', { status: 401 })))
  renderApp()
  expect(await screen.findByText(/backend unreachable/i)).toBeInTheDocument()
})
