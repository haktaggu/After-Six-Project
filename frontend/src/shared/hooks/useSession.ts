import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchCsrf, getSession, login, logout, signup } from '../api/accounts'
import { ApiClientError, clearCsrfToken, SESSION_EXPIRED_EVENT, setCsrfToken } from '../api/client'
import type { LoginRequest, SessionResponse, SessionState, SignupRequest } from '../api/types'

export interface SessionActions {
  state: SessionState
  refreshSession: () => Promise<void>
  signIn: (body: LoginRequest) => Promise<void>
  signUp: (body: SignupRequest) => Promise<void>
  signOut: () => Promise<void>
}

export function useSession(): SessionActions {
  const [state, setState] = useState<SessionState>({ status: 'loading', session: null, error: null })
  const requestId = useRef(0)

  const refreshSession = useCallback(async (): Promise<void> => {
    const currentRequest = ++requestId.current
    try {
      const session = await getSession()
      if (currentRequest !== requestId.current) return
      setCsrfToken(session.csrf_token)
      setState({ status: 'authenticated', session, error: null })
    } catch (error) {
      if (currentRequest !== requestId.current) return
      clearCsrfToken()
      if (error instanceof ApiClientError && error.status === 401) {
        setState({ status: 'anonymous', session: null, error: null })
      } else {
        setState({ status: 'unavailable', session: null,
          error: error instanceof Error ? error.message : 'Unable to check your login' })
      }
    }
  }, [])

  const startSession = useCallback(async (request: () => Promise<SessionResponse>): Promise<void> => {
    const currentRequest = ++requestId.current
    try {
      const { csrf_token } = await fetchCsrf()
      if (currentRequest !== requestId.current) return
      setCsrfToken(csrf_token)
      const session = await request()
      if (currentRequest !== requestId.current) return
      setCsrfToken(session.csrf_token)
      setState({ status: 'authenticated', session, error: null })
    } catch (error) {
      if (currentRequest === requestId.current) {
        clearCsrfToken()
        setState({ status: 'anonymous', session: null, error: null })
      }
      throw error
    }
  }, [])

  const signIn = (body: LoginRequest) => startSession(() => login(body))
  const signUp = (body: SignupRequest) => startSession(() => signup(body))

  const signOut = useCallback(async (): Promise<void> => {
    const currentRequest = ++requestId.current
    try {
      await logout()
    } catch (error) {
      if (!(error instanceof ApiClientError && error.status === 401)) throw error
    }
    if (currentRequest !== requestId.current) return
    clearCsrfToken()
    setState({ status: 'anonymous', session: null, error: null })
  }, [])

  useEffect(() => {
    let active = true
    const invalidateRequests = () => { requestId.current++ }
    const expireSession = () => {
      invalidateRequests()
      clearCsrfToken()
      setState({ status: 'anonymous', session: null, error: null })
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, expireSession)
    void Promise.resolve().then(() => { if (active) return refreshSession() })
    return () => {
      active = false
      invalidateRequests()
      window.removeEventListener(SESSION_EXPIRED_EVENT, expireSession)
    }
  }, [refreshSession])

  useEffect(() => {
    if (state.status !== 'authenticated') return
    const expiresIn = Date.parse(state.session.expires_at) - Date.now()
    const timer = window.setTimeout(() => {
      requestId.current++
      clearCsrfToken()
      setState({ status: 'anonymous', session: null, error: null })
    }, Math.max(0, expiresIn))
    return () => window.clearTimeout(timer)
  }, [state])

  return { state, refreshSession, signIn, signUp, signOut }
}
