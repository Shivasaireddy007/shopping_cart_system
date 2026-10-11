import { create } from 'zustand'

/** One API call, as shown in the request inspector. */
export type LoggedRequest = {
  id: number
  method: string
  path: string
  status: number
  /** Round trip measured in the browser. */
  ms: number
  /** Time spent in the API, from its Server-Timing header. */
  serverMs: number | null
  /** Whether Redis served it (catalog endpoints only), from X-Cache. */
  cache: 'HIT' | 'MISS' | null
}

type RequestLog = {
  requests: LoggedRequest[]
  add: (request: Omit<LoggedRequest, 'id'>) => void
}

const KEEP = 25
let nextId = 1

export const useRequestLog = create<RequestLog>((set) => ({
  requests: [],
  add: (request) => set((s) => ({ requests: [{ ...request, id: nextId++ }, ...s.requests].slice(0, KEEP) })),
}))

/** "app;dur=3.4" -> 3.4 */
export function serverDuration(header: string | null): number | null {
  const match = header?.match(/dur=([\d.]+)/)
  return match ? Number(match[1]) : null
}
