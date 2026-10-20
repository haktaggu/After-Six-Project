export async function checkHealth(signal?: AbortSignal): Promise<void> {
  const response = await fetch('/api/health', { signal })
  if (!response.ok) throw new Error('API unavailable')
  const data: unknown = await response.json()
  if (typeof data !== 'object' || data === null || !('status' in data) || data.status !== 'ok') {
    throw new Error('Unexpected health response')
  }
}
