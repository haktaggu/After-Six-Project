import type { FieldError } from './types'

export class ApiClientError extends Error {
  status: number
  code: string
  fields: FieldError[]

  constructor(status: number, code: string, message: string, fields: FieldError[] = []) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export type ApiRequestOptions = Omit<RequestInit, 'body'> & { body?: unknown }
export const SESSION_EXPIRED_EVENT = 'oursjsu:session-expired'
let csrfToken: string | null = null

export function setCsrfToken(token: string): void {
  csrfToken = token
}

export function clearCsrfToken(): void {
  csrfToken = null
}

export function queryString(query: object): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue
    if (value === null) throw new ApiClientError(422, 'VALIDATION_ERROR', 'Omit unused filters')
    params.set(key, String(value))
  }
  const encoded = params.toString()
  return encoded ? '?' + encoded : ''
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, ...requestOptions } = options
  const requestToken = csrfToken
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }

  let response: Response
  try {
    response = await fetch('/api' + path, {
      ...requestOptions,
      method,
      headers,
      credentials: 'include',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw new ApiClientError(0, 'NETWORK_ERROR', 'Unable to reach the server')
  }

  if (response.status === 401 && requestToken === csrfToken
    && !['/auth/login', '/auth/csrf', '/auth/session'].includes(path)) {
    clearCsrfToken()
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  }

  if (response.status === 204 && response.ok) return undefined as T

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new ApiClientError(response.status, response.ok ? 'INVALID_RESPONSE' : 'HTTP_ERROR',
      response.ok ? 'The server returned an invalid response' : 'Request failed')
  }

  if (!response.ok) {
    if (typeof payload === 'object' && payload !== null && 'error' in payload) {
      const error = payload.error
      if (typeof error === 'object' && error !== null && 'code' in error && 'message' in error
        && typeof error.code === 'string' && typeof error.message === 'string') {
        const fields = 'fields' in error && Array.isArray(error.fields)
          ? error.fields.filter((field): field is FieldError => typeof field === 'object' && field !== null
            && typeof field.path === 'string' && typeof field.message === 'string')
          : []
        throw new ApiClientError(response.status, error.code, error.message, fields)
      }
    }
    const message = typeof payload === 'object' && payload !== null && 'detail' in payload
      && typeof payload.detail === 'string' ? payload.detail : 'Request failed'
    throw new ApiClientError(response.status, 'HTTP_ERROR', message)
  }

  return payload as T
}
