import { useEffect, useRef, useState } from 'react'

interface SwitchableUser {
  userId: string
  password: string
  label: string
  role: string
}

interface TopbarProps {
  title: string
  description?: string
  onLogout: () => void
  currentUser?: string
  currentUserId?: string
  currentUserRole?: string
  onUserClick?: () => void
  onSwitchUser?: (userId: string, password: string) => Promise<void>
  switchableUsers?: SwitchableUser[]
}

const Topbar: React.FC<TopbarProps> = ({
  title,
  description,
  onLogout,
  currentUser,
  currentUserId,
  currentUserRole,
  onUserClick,
  onSwitchUser,
  switchableUsers,
}) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const [switching, setSwitching] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  const handleSwitch = async (userId: string, password: string) => {
    if (!onSwitchUser) return
    setSwitching(true)
    try {
      await onSwitchUser(userId, password)
      setMenuOpen(false)
    } finally {
      setSwitching(false)
    }
  }

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, minWidth: 0 }}>
        <h1 className="topbar__title">{title}</h1>
        {description && <span className="topbar__desc">{description}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {(currentUserRole || currentUserId) && (
          <span
            className="stat-pill stat-pill--info"
            title="当前工作流身份"
            style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {currentUserRole && <span className="stat-pill__value">{currentUserRole}</span>}
            {currentUserRole && currentUserId && <span>·</span>}
            {currentUserId && (
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>{currentUserId}</span>
            )}
          </span>
        )}

        <div ref={menuRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="topbar__user-trigger"
            onClick={() => setMenuOpen(o => !o)}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            <span className="topbar__avatar">{(currentUser || 'U').charAt(0).toUpperCase()}</span>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
              {currentUser || '用户'}
            </span>
            <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>▾</span>
          </button>

          {menuOpen && (
            <div
              role="menu"
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: 240,
                backgroundColor: 'var(--surface-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-xl)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 1000,
                overflow: 'hidden',
                animation: 'scaleIn 0.15s ease',
              }}
            >
              <div style={{ padding: '10px 14px 6px', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                切换用户
              </div>

              {switchableUsers?.map(user => {
                const isActive = currentUser === user.userId || currentUser === user.label
                return (
                  <button
                    key={user.userId}
                    type="button"
                    role="menuitem"
                    disabled={switching || isActive}
                    onClick={() => handleSwitch(user.userId, user.password)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '8px 14px',
                      textAlign: 'left',
                      background: isActive ? 'var(--surface-secondary)' : 'transparent',
                      opacity: switching ? 0.6 : 1,
                      cursor: switching || isActive ? 'default' : 'pointer',
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="topbar__avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
                        {user.label.charAt(0)}
                      </span>
                      <span>
                        <div style={{ fontSize: 13, fontWeight: 500 }}>{user.label}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{user.role}</div>
                      </span>
                    </span>
                    {isActive && <span style={{ color: 'var(--status-success)', fontWeight: 700 }}>✓</span>}
                  </button>
                )
              })}

              <div style={{ height: 1, background: 'var(--border-subtle)', margin: '4px 0' }} />

              <button type="button" role="menuitem" className="btn btn--ghost" style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }} onClick={() => { onUserClick?.(); setMenuOpen(false) }}>
                个人信息
              </button>
              <button
                type="button"
                role="menuitem"
                className="btn btn--ghost"
                style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0, color: 'var(--status-error)' }}
                onClick={onLogout}
              >
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Topbar
