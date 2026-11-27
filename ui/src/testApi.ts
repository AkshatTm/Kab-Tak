// A fake backend for component tests: records requests, answers by "METHOD /path".
import { vi } from 'vitest'

export const CATEGORIES = [{ id: 'cat-dsa', name: 'DSA', parent_id: null }]
export const PART_TYPES = [
  { id: 'pt-practice', key: 'practice_problem', unit: 'problems', label: 'Practice problems' },
  { id: 'pt-other', key: 'other', unit: 'items', label: 'Other' },
]
export const CARD = {
  title: 'Graph problems',
  raw_text: '2 graph problems',
  category_id: 'cat-dsa',
  estimate_min: null,
  tentative: false,
  familiarity: null,
  source: 'chat' as const,
  parts: [{ part_type_id: 'pt-practice', planned_qty: 2 }],
}

export type Sent = { route: string; body: unknown; token: string | null }

export function fakeBackend(routes: Record<string, () => Response> = {}) {
  const all: Record<string, () => Response> = {
    'GET /api/health': () => Response.json({ status: 'ok', version: '0.1.0', db: 'ok' }),
    'GET /api/categories': () => Response.json(CATEGORIES),
    'GET /api/part-types': () => Response.json(PART_TYPES),
    'POST /api/tasks': () => Response.json({ id: 't1' }, { status: 201 }),
    'POST /api/corrections': () => Response.json({ id: 'c1' }, { status: 201 }),
    ...routes,
  }
  const sent: Sent[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const route = `${init?.method ?? 'GET'} ${new URL(url).pathname}`
      sent.push({
        route,
        body: init?.body ? JSON.parse(init.body as string) : undefined,
        token: new Headers(init?.headers).get('X-KabTak-Token'),
      })
      const answer = all[route]
      return answer ? answer() : new Response('no such route', { status: 404 })
    }),
  )
  return { sent, posts: (route: string) => sent.filter((s) => s.route === route) }
}
