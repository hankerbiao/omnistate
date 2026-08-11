import { beforeEach, describe, expect, it } from 'vitest'

import { resolveWebSocketUrl } from './terminalUrl'

describe('resolveWebSocketUrl', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('resolves a relative API base URL against the current HTTPS origin', () => {
    localStorage.setItem('jwt_token', 'test-token')

    const result = new URL(
      resolveWebSocketUrl(120, 40, '/api/v1', 'https://dml.example.com'),
    )

    expect(result.origin).toBe('wss://dml.example.com')
    expect(result.pathname).toBe('/api/v1/terminal/ws')
    expect(result.searchParams.get('token')).toBe('test-token')
    expect(result.searchParams.get('cols')).toBe('120')
    expect(result.searchParams.get('rows')).toBe('40')
  })
})
