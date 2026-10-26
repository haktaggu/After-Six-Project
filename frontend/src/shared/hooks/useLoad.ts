import { useCallback, useEffect, useState } from 'react'

export function useLoad<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)
  const reload = useCallback(() => setVersion(n => n + 1), [])

  useEffect(() => {
    const ctrl = new AbortController()
    void Promise.resolve().then(() => {
      if (ctrl.signal.aborted) return
      setLoading(true)
      setError(null)
      return load(ctrl.signal).then(res => {
        if (!ctrl.signal.aborted) setData(res)
      }).catch((err: unknown) => {
        if (!ctrl.signal.aborted) setError(err)
      }).finally(() => {
        if (!ctrl.signal.aborted) setLoading(false)
      })
    })
    return () => ctrl.abort()
  }, [load, version])

  return { data, error, loading, reload }
}
