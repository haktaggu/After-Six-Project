import { useEffect, useState } from 'react'
import { checkHealth } from '../api/health'

type ApiHealth = 'loading' | 'connected' | 'unavailable'

export function useApiHealth(): ApiHealth {
  const [status, setStatus] = useState<ApiHealth>('loading')

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    let active = true
    checkHealth(controller.signal)
      .then(() => { if (active) setStatus('connected') })
      .catch(() => { if (active) setStatus('unavailable') })
      .finally(() => window.clearTimeout(timeout))
    return () => {
      active = false
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [])

  return status
}
