import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api/client'
import { serverDuration, useRequestLog } from './requests'

afterEach(() => vi.restoreAllMocks())

describe('request log', () => {
  it('reads the server time from Server-Timing', () => {
    expect(serverDuration('app;dur=3.4')).toBe(3.4)
    expect(serverDuration(null)).toBeNull()
  })

  it('records API calls with server time and cache result', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('[]', { headers: { 'Content-Type': 'application/json', 'Server-Timing': 'app;dur=2.5', 'X-Cache': 'HIT' } }),
    )

    await api.GET('/api/v1/categories')

    expect(useRequestLog.getState().requests[0]).toMatchObject({
      method: 'GET',
      path: '/categories',
      status: 200,
      serverMs: 2.5,
      cache: 'HIT',
    })
  })
})
