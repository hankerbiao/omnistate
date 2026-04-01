import { useEffect, useRef, useState } from 'react'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'closed' | 'error'

interface SessionMeta {
  sessionId: string
  shell: string
  cwd: string
  host: string
  port: number
  username: string
}

interface ConnectionForm {
  host: string
  port: string
  username: string
  password: string
}

const STORAGE_KEY = 'dml_terminal_ssh_credentials'

function resolveWebSocketUrl(cols: number, rows: number): string {
  const token = localStorage.getItem('jwt_token') || ''
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const httpUrl = new URL(apiBaseUrl)
  const protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  const socketUrl = new URL(`${protocol}//${httpUrl.host}/api/v1/terminal/ws`)

  socketUrl.searchParams.set('token', token)
  socketUrl.searchParams.set('cols', String(cols))
  socketUrl.searchParams.set('rows', String(rows))
  return socketUrl.toString()
}

function loadSavedForm(): ConnectionForm {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return { host: '', port: '22', username: '', password: '' }
    }

    const parsed = JSON.parse(raw) as Partial<ConnectionForm>
    return {
      host: parsed.host || '',
      port: parsed.port || '22',
      username: parsed.username || '',
      password: parsed.password || '',
    }
  } catch {
    return { host: '', port: '22', username: '', password: '' }
  }
}

const statusLabelMap: Record<ConnectionState, string> = {
  idle: '未连接',
  connecting: '连接中',
  connected: '已连接',
  closed: '已断开',
  error: '连接异常',
}

const TerminalPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const terminalRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const connectionStateRef = useRef<ConnectionState>('idle')
  const isTerminalReadyRef = useRef(false)
  const fitFrameRef = useRef<number | null>(null)

  const [connectionState, setConnectionState] = useState<ConnectionState>('idle')
  const [sessionMeta, setSessionMeta] = useState<SessionMeta | null>(null)
  const [lastError, setLastError] = useState('')
  const [form, setForm] = useState<ConnectionForm>(() => loadSavedForm())

  useEffect(() => {
    connectionStateRef.current = connectionState
  }, [connectionState])

  const scheduleFit = () => {
    if (fitFrameRef.current !== null) {
      window.cancelAnimationFrame(fitFrameRef.current)
    }

    fitFrameRef.current = window.requestAnimationFrame(() => {
      const terminal = terminalRef.current
      const fitAddon = fitAddonRef.current
      const container = containerRef.current

      if (!terminal || !fitAddon || !container || !container.isConnected || !isTerminalReadyRef.current) {
        return
      }

      try {
        fitAddon.fit()
      } catch {
        // xterm 在 viewport 尚未完成初始化或已销毁时会抛内部异常，这里直接忽略。
      }
    })
  }

  useEffect(() => {
    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: '"SF Mono", "JetBrains Mono", "Fira Code", monospace',
      theme: {
        background: '#0b1220',
        foreground: '#d7e0ea',
        cursor: '#79ffe1',
        selectionBackground: 'rgba(121, 255, 225, 0.22)',
      },
      scrollback: 2000,
    })
    const fitAddon = new FitAddon()

    terminal.loadAddon(fitAddon)
    terminalRef.current = terminal
    fitAddonRef.current = fitAddon

    if (containerRef.current) {
      terminal.open(containerRef.current)
      isTerminalReadyRef.current = true
      scheduleFit()
      terminal.writeln('\x1b[36mDML SSH Terminal\x1b[0m')
      terminal.writeln('填写远程服务器信息后点击“连接终端”。')
    }

    resizeObserverRef.current = new ResizeObserver(() => {
      scheduleFit()
      const socket = socketRef.current
      if (
        socket &&
        socket.readyState === WebSocket.OPEN &&
        connectionStateRef.current === 'connected'
      ) {
        socket.send(
          JSON.stringify({
            type: 'resize',
            cols: terminal.cols,
            rows: terminal.rows,
          }),
        )
      }
    })

    if (containerRef.current) {
      resizeObserverRef.current.observe(containerRef.current)
    }

    return () => {
      isTerminalReadyRef.current = false
      if (fitFrameRef.current !== null) {
        window.cancelAnimationFrame(fitFrameRef.current)
        fitFrameRef.current = null
      }
      resizeObserverRef.current?.disconnect()
      resizeObserverRef.current = null
      socketRef.current?.close()
      socketRef.current = null
      terminal.dispose()
      terminalRef.current = null
      fitAddonRef.current = null
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(form))
  }, [form])

  useEffect(() => {
    const terminal = terminalRef.current
    if (!terminal) {
      return
    }

    const disposable = terminal.onData((data) => {
      const socket = socketRef.current
      if (!socket || socket.readyState !== WebSocket.OPEN || connectionState !== 'connected') {
        return
      }
      socket.send(JSON.stringify({ type: 'input', data }))
    })

    return () => {
      disposable.dispose()
    }
  }, [connectionState])

  const updateField = (field: keyof ConnectionForm, value: string) => {
    setForm((previous) => ({ ...previous, [field]: value }))
  }

  const connectTerminal = () => {
    const terminal = terminalRef.current
    const fitAddon = fitAddonRef.current
    if (!terminal || !fitAddon) {
      return
    }

    if (!form.host.trim() || !form.username.trim() || !form.password || !form.port.trim()) {
      setConnectionState('error')
      setLastError('请完整填写 host、port、username、password')
      terminal.writeln('\r\n\x1b[31m[error] missing SSH connection fields\x1b[0m')
      return
    }

    const port = Number(form.port)
    if (!Number.isInteger(port) || port <= 0 || port > 65535) {
      setConnectionState('error')
      setLastError('端口必须是 1-65535 的整数')
      terminal.writeln('\r\n\x1b[31m[error] invalid SSH port\x1b[0m')
      return
    }

    socketRef.current?.close()
    scheduleFit()
    setConnectionState('connecting')
    setLastError('')
    setSessionMeta(null)

    const socket = new WebSocket(resolveWebSocketUrl(terminal.cols, terminal.rows))
    socketRef.current = socket

    socket.onopen = () => {
      terminal.writeln(`\r\n\x1b[32m[connecting ${form.username}@${form.host}:${port}]\x1b[0m`)
      socket.send(
        JSON.stringify({
          type: 'connect',
          host: form.host.trim(),
          port,
          username: form.username.trim(),
          password: form.password,
        }),
      )
    }

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: string
        data?: string
        message?: string
        session_id?: string
        shell?: string
        cwd?: string
        code?: number
        host?: string
        port?: number
        username?: string
      }

      if (payload.type === 'session') {
        setConnectionState('connected')
        setSessionMeta({
          sessionId: payload.session_id || '',
          shell: payload.shell || '',
          cwd: payload.cwd || '',
          host: payload.host || '',
          port: payload.port || port,
          username: payload.username || '',
        })
        terminal.writeln(
          `\r\n\x1b[90m[session ${payload.session_id} ${payload.username}@${payload.host}:${payload.port}]\x1b[0m`,
        )
        return
      }

      if (payload.type === 'output') {
        terminal.write(payload.data || '')
        return
      }

      if (payload.type === 'error') {
        const message = payload.message || 'terminal error'
        setConnectionState('error')
        setLastError(message)
        terminal.writeln(`\r\n\x1b[31m[error] ${message}\x1b[0m`)
        return
      }

      if (payload.type === 'exit') {
        setConnectionState('closed')
        terminal.writeln(`\r\n\x1b[33m[process exited: ${payload.code ?? 'unknown'}]\x1b[0m`)
        return
      }
    }

    socket.onerror = () => {
      setConnectionState('error')
      setLastError('WebSocket 连接失败')
      terminal.writeln('\r\n\x1b[31m[websocket error]\x1b[0m')
    }

    socket.onclose = () => {
      setConnectionState((current) => (current === 'error' ? current : 'closed'))
      socketRef.current = null
      terminal.writeln('\r\n\x1b[90m[disconnected]\x1b[0m')
    }
  }

  const disconnectTerminal = () => {
    socketRef.current?.close()
  }

  const clearSavedCredentials = () => {
    localStorage.removeItem(STORAGE_KEY)
    setForm({ host: '', port: '22', username: '', password: '' })
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Remote SSH Terminal</h2>
          <p style={styles.subtitle}>输入远程服务器地址与账号信息，通过后端 SSH 桥接到 xterm.js。</p>
        </div>
        <div style={styles.actions}>
          <button style={styles.primaryButton} onClick={connectTerminal}>
            连接终端
          </button>
          <button style={styles.secondaryButton} onClick={disconnectTerminal}>
            断开
          </button>
          <button style={styles.secondaryButton} onClick={clearSavedCredentials}>
            清空凭据
          </button>
        </div>
      </div>

      <div style={styles.formCard}>
        <div style={styles.formGrid}>
          <label style={styles.field}>
            <span style={styles.fieldLabel}>Host</span>
            <input
              style={styles.input}
              value={form.host}
              onChange={(event) => updateField('host', event.target.value)}
              placeholder="192.168.1.10"
            />
          </label>
          <label style={styles.field}>
            <span style={styles.fieldLabel}>Port</span>
            <input
              style={styles.input}
              value={form.port}
              onChange={(event) => updateField('port', event.target.value)}
              placeholder="22"
            />
          </label>
          <label style={styles.field}>
            <span style={styles.fieldLabel}>Username</span>
            <input
              style={styles.input}
              value={form.username}
              onChange={(event) => updateField('username', event.target.value)}
              placeholder="root"
            />
          </label>
          <label style={styles.field}>
            <span style={styles.fieldLabel}>Password</span>
            <input
              style={styles.input}
              type="password"
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
              placeholder="password"
            />
          </label>
        </div>
      </div>

      <div style={styles.metaGrid}>
        <div style={styles.metaCard}>
          <span style={styles.metaLabel}>状态</span>
          <strong>{statusLabelMap[connectionState]}</strong>
        </div>
        <div style={styles.metaCard}>
          <span style={styles.metaLabel}>目标主机</span>
          <strong>{sessionMeta ? `${sessionMeta.username}@${sessionMeta.host}:${sessionMeta.port}` : '-'}</strong>
        </div>
        <div style={styles.metaCard}>
          <span style={styles.metaLabel}>Shell</span>
          <strong>{sessionMeta?.shell || '-'}</strong>
        </div>
        <div style={styles.metaCard}>
          <span style={styles.metaLabel}>会话 ID</span>
          <strong>{sessionMeta?.sessionId || '-'}</strong>
        </div>
      </div>

      <div style={styles.terminalCard}>
        <div ref={containerRef} style={styles.terminalViewport} />
      </div>

      <div style={styles.notice}>
        账号和密码当前保存在浏览器本地 `localStorage`，仅适合受控内网环境。
        {lastError ? <span style={styles.errorText}> 最近错误: {lastError}</span> : null}
      </div>
    </div>
  )
}

const styles = {
  page: {
    padding: '24px',
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
  } as const,
  title: {
    margin: 0,
    fontSize: '28px',
    color: 'var(--text-primary)',
  } as const,
  subtitle: {
    margin: '8px 0 0',
    color: 'var(--text-secondary)',
  } as const,
  actions: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
  } as const,
  primaryButton: {
    padding: '10px 16px',
    borderRadius: '12px',
    border: 'none',
    background: 'linear-gradient(135deg, #2dd4bf, #0ea5e9)',
    color: '#04111f',
    fontWeight: 700,
    cursor: 'pointer',
  } as const,
  secondaryButton: {
    padding: '10px 16px',
    borderRadius: '12px',
    border: '1px solid var(--border-default)',
    background: 'transparent',
    color: 'var(--text-primary)',
    fontWeight: 600,
    cursor: 'pointer',
  } as const,
  formCard: {
    padding: '18px',
    borderRadius: '18px',
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background:
      'linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 247, 251, 0.96))',
    boxShadow: '0 16px 38px rgba(15, 23, 42, 0.08)',
  } as const,
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '14px',
  } as const,
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  } as const,
  fieldLabel: {
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#475569',
  } as const,
  input: {
    borderRadius: '12px',
    border: '1px solid #cbd5e1',
    backgroundColor: '#ffffff',
    color: '#0f172a',
    padding: '12px 14px',
    outline: 'none',
    boxShadow: 'inset 0 1px 2px rgba(15, 23, 42, 0.04)',
  } as const,
  metaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '12px',
  } as const,
  metaCard: {
    padding: '14px 16px',
    borderRadius: '14px',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-secondary)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  } as const,
  metaLabel: {
    color: 'var(--text-secondary)',
    fontSize: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  } as const,
  terminalCard: {
    borderRadius: '18px',
    padding: '18px',
    background:
      'radial-gradient(circle at top left, rgba(45, 212, 191, 0.08), transparent 32%), #050b14',
    border: '1px solid rgba(148, 163, 184, 0.18)',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.28)',
  } as const,
  terminalViewport: {
    minHeight: '60vh',
    width: '100%',
  } as const,
  notice: {
    color: 'var(--text-secondary)',
    fontSize: '13px',
  } as const,
  errorText: {
    color: '#fca5a5',
  } as const,
}

export default TerminalPage
