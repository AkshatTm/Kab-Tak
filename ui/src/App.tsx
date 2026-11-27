import { useQuery } from '@tanstack/react-query'
import { getHealth } from './api/client'
import ChatScreen from './components/ChatScreen'

export default function App() {
  const { data, isPending, isError } = useQuery({ queryKey: ['health'], queryFn: getHealth })
  let status = 'Connected'
  if (isPending) status = 'Connecting…'
  if (isError) status = 'Backend unreachable'
  return (
    <div className="flex h-dvh flex-col">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2">
        <h1 className="text-lg font-semibold">Kab Tak</h1>
        {/* the words carry the state; the dot's shape (filled or ring) only repeats it */}
        <p
          title={data && `Database ${data.db}, version ${data.version}`}
          className={`flex items-center gap-2 text-sm ${isError ? 'text-error' : 'text-dim'}`}
        >
          <span
            aria-hidden
            className={`size-2 rounded-full border border-current ${data && !isError ? 'bg-current' : ''}`}
          />
          {status}
        </p>
      </header>
      <main className="flex min-h-0 flex-1 flex-col">
        <ChatScreen />
      </main>
    </div>
  )
}
