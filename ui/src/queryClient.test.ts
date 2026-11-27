import { MutationObserver, onlineManager } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { makeQueryClient } from './queryClient'

afterEach(() => onlineManager.setOnline(true))

// the backend is on this machine: losing the network must not pause requests to it
it('sends requests while the browser reports it is offline', async () => {
  onlineManager.setOnline(false)
  const send = vi.fn(async () => 'ok')
  const mutation = new MutationObserver(makeQueryClient(), { mutationFn: send })
  void mutation.mutate()
  await vi.waitFor(() => expect(send).toHaveBeenCalled())
})
