let sessionToken = ''

export function setSessionToken(token: string): void {
  sessionToken = token
}

export function getSessionToken(): string {
  if (!sessionToken && typeof window !== 'undefined') {
    const fragment = new URLSearchParams(window.location.hash.slice(1))
    const token = fragment.get('token')
    if (token) {
      sessionToken = token
      fragment.delete('token')
      const suffix = fragment.size ? `#${fragment.toString()}` : ''
      window.history.replaceState(null, '', window.location.pathname + window.location.search + suffix)
    }
  }
  return sessionToken
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use a local API path')
  const token = getSessionToken()
  if (!token) throw new Error('Open the dashboard URL printed by SentriFlow to start a session')
  const headers = new Headers(options.headers)
  headers.set('X-SentriFlow-Token', token)
  if (options.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(`/api${path}`, { ...options, headers, credentials: 'omit' })
  if (!response.ok) throw new Error(`SentriFlow API returned ${response.status}`)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
