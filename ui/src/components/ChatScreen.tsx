import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { getCategories, getPartTypes, postChat, type ChatResponse } from '../api/client'
import TaskCard from './TaskCard'

type Entry = { id: number } & ({ text: string } | { response: ChatResponse })

/** The conversation lives in memory only (D8). */
export default function ChatScreen() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [text, setText] = useState('')
  const nextId = useRef(0)
  const input = useRef<HTMLTextAreaElement>(null)
  const end = useRef<HTMLDivElement>(null)

  const categories = useQuery({ queryKey: ['categories'], queryFn: getCategories })
  const partTypes = useQuery({ queryKey: ['part-types'], queryFn: getPartTypes })
  const chat = useMutation({
    mutationFn: ({ message }: { message: string; id: number }) => postChat(message),
    onSuccess: (response) => setEntries((e) => [...e, { id: nextId.current++, response }]),
    onError: (_, { message, id }) => {
      setEntries((e) => e.filter((entry) => entry.id !== id))
      setText((typed) => typed || message) // never lose what the user wrote
    },
  })

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'nearest' })
  }, [entries, chat.isPending])

  function send() {
    const message = text.trim()
    if (!message || chat.isPending) return
    const id = nextId.current++
    setEntries((e) => [...e, { id, text: message }])
    setText('')
    chat.mutate({ message, id })
  }

  const listsFailed = categories.isError || partTypes.isError

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4">
        <div className="mx-auto grid max-w-2xl gap-3 py-4">
          {entries.length === 0 && (
            <p className="text-dim">
              Type what you're about to work on, with your own time guess. For example: “Solve 2
              graph problems, I think 40 min.”
            </p>
          )}
          <ol aria-label="Conversation" aria-live="polite" className="grid gap-3">
            {entries.map((entry) =>
              'text' in entry ? (
                <li
                  key={entry.id}
                  className="max-w-[85%] justify-self-end rounded-lg bg-line px-3 py-2 break-words whitespace-pre-wrap"
                >
                  <span className="sr-only">You: </span>
                  {entry.text}
                </li>
              ) : (
                <li key={entry.id} className="grid gap-2">
                  <p>{entry.response.reply}</p>
                  {categories.data && partTypes.data
                    ? entry.response.cards.map((card, i) => (
                        <TaskCard
                          key={i}
                          card={card}
                          parseJson={entry.response.parse_json}
                          categories={categories.data}
                          partTypes={partTypes.data}
                          autoFocus={i === 0}
                          onSaved={() => input.current?.focus()}
                        />
                      ))
                    : entry.response.cards.length > 0 &&
                      !listsFailed && <p className="text-dim">Loading the card…</p>}
                </li>
              ),
            )}
          </ol>
          {chat.isPending && <p className="text-dim">Reading your message…</p>}
          {listsFailed && (
            <p role="alert" className="text-error">
              Couldn't load categories and part types.{' '}
              <button
                type="button"
                className="btn text-sm text-ink"
                onClick={() => {
                  void categories.refetch()
                  void partTypes.refetch()
                }}
              >
                Try again
              </button>
            </p>
          )}
          {chat.isError && (
            <p role="alert" className="text-error">
              Couldn't send: {chat.error.message}. Your text is back in the box.
            </p>
          )}
          <div ref={end} />
        </div>
      </div>

      <form
        className="border-t border-line px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        <div className="mx-auto flex max-w-2xl items-end gap-2">
          <textarea
            ref={input}
            autoFocus
            aria-label="Message"
            rows={2}
            maxLength={4000}
            placeholder="Task and your guess"
            className="field flex-1 resize-none"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return
              e.preventDefault()
              send()
            }}
          />
          <button type="submit" className="btn" disabled={!text.trim() || chat.isPending}>
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
