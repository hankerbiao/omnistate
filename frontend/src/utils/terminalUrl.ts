export function resolveWebSocketUrl(
  cols: number,
  rows: number,
  apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  pageOrigin = window.location.origin,
): string {
  const token = localStorage.getItem('jwt_token') || ''
  const httpUrl = new URL(apiBaseUrl, pageOrigin)
  const protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  const socketUrl = new URL(`${protocol}//${httpUrl.host}/api/v1/terminal/ws`)

  socketUrl.searchParams.set('token', token)
  socketUrl.searchParams.set('cols', String(cols))
  socketUrl.searchParams.set('rows', String(rows))
  return socketUrl.toString()
}
