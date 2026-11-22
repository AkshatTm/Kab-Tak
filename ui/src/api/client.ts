import type { paths } from './schema'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765'
const TOKEN = import.meta.env.VITE_API_TOKEN ?? ''

export type Health = paths['/api/health']['get']['responses']['200']['content']['application/json']

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { 'X-KabTak-Token': TOKEN } })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return (await res.json()) as T
}

export const getHealth = () => get<Health>('/api/health')
