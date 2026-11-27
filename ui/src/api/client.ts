import type { components, paths } from './schema'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765'
const TOKEN = import.meta.env.VITE_API_TOKEN ?? ''

type Schema = components['schemas']
export type Health = paths['/api/health']['get']['responses']['200']['content']['application/json']
export type TaskCreate = Schema['TaskCreate']
export type ChatResponse = Schema['ChatResponse']
export type Category = Schema['CategoryOut']
export type PartType = Schema['PartTypeOut']

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** FastAPI answers `{detail: string}` or `{detail: [{msg}]}`. */
async function errorText(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
  if (typeof body?.detail === 'string') return body.detail
  if (Array.isArray(body?.detail)) {
    return body.detail.map((e: { msg?: string }) => e.msg).join('; ')
  }
  return `the backend answered ${res.status}`
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'X-KabTak-Token': TOKEN }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BASE}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(res.status, await errorText(res))
  return (await res.json()) as T
}

export const getHealth = () => request<Health>('/api/health')
export const getCategories = () => request<Category[]>('/api/categories')
export const getPartTypes = () => request<PartType[]>('/api/part-types')
export const postChat = (text: string) => request<ChatResponse>('/api/chat', { text })
export const createTask = (task: TaskCreate) => request<Schema['TaskOut']>('/api/tasks', task)
export const postCorrection = (correction: Schema['CorrectionIn']) =>
  request<Schema['CorrectionOut']>('/api/corrections', correction)
