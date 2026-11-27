import { QueryClient } from '@tanstack/react-query'

/** The backend runs on this machine, so a lost network must never pause requests to it. */
export const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { networkMode: 'always' },
      mutations: { networkMode: 'always' },
    },
  })
