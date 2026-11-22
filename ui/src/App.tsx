import { useQuery } from '@tanstack/react-query'
import { getHealth } from './api/client'

export default function App() {
  const { data, isPending, isError } = useQuery({ queryKey: ['health'], queryFn: getHealth })
  let text = `Backend: ${data?.status} · db ${data?.db} · v${data?.version}`
  if (isPending) text = 'Connecting…'
  if (isError) text = 'Backend unreachable'
  return (
    <main className="grid min-h-screen place-items-center bg-stone-950 text-stone-100">
      <h1 className="text-xl font-medium">Kab Tak · {text}</h1>
    </main>
  )
}
