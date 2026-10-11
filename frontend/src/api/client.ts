import createClient, { type Middleware } from 'openapi-fetch'

import { useAuth } from '../stores/auth'
import type { components, paths } from './schema'

export type Product = components['schemas']['ProductOut']
export type Category = components['schemas']['CategoryOut']
export type Cart = components['schemas']['CartOut']
export type User = components['schemas']['UserOut']
export type ProductCreate = components['schemas']['ProductCreate']

const baseUrl = import.meta.env.VITE_API_URL ?? ''

export const api = createClient<paths>({ baseUrl })

/** Errors from the API carry the HTTP status and the server's message. */
export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, body: unknown) {
    const detail = (body as { detail?: unknown } | null)?.detail
    super(typeof detail === 'string' ? detail : `Request failed (${status})`)
    this.status = status
    this.body = body
  }
}

let refreshing: Promise<boolean> | null = null

/** Swaps the refresh token for a new pair. Concurrent 401s share one refresh request. */
function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    const refreshToken = useAuth.getState().refreshToken
    if (!refreshToken) return false
    const response = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      useAuth.getState().logout()
      return false
    }
    useAuth.getState().setTokens(await response.json())
    return true
  })().finally(() => {
    refreshing = null
  })
  return refreshing
}

const auth: Middleware = {
  onRequest({ request }) {
    const token = useAuth.getState().accessToken
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || request.url.endsWith('/auth/refresh') || !useAuth.getState().refreshToken) {
      return response
    }
    if (!(await refreshTokens())) return response

    const retry = request.clone()
    retry.headers.set('Authorization', `Bearer ${useAuth.getState().accessToken}`)
    return fetch(retry)
  },
}

api.use(auth)

/** Unwraps an openapi-fetch result, throwing ApiError on failure. */
export async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await promise
  if (error !== undefined || !response.ok) throw new ApiError(response.status, error ?? null)
  return data as T
}
