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
  onUserClick?: () => void
  onSwitchUser?: (userId: string, password: string) => Promise<void>
  switchableUsers?: SwitchableUser[]
}

const Topbar: React.FC<TopbarProps> = ({ title, description, onLogout, currentUser, onUserClick, onSwitchUser, switchableUsers }) => {
  const [menuOpen, setMenuOpen] = useState(false)
  const [switching, setSwitching] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭菜单
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
    <header style={styles.topbar}>
      <div style={styles.left}>
        <h1 style={styles.title}>{title}</h1>
        {description && (
          <span style={styles.description}>{description}</span>
        )}
      </div>
      <div style={styles.right}>
        <div ref={menuRef} style={{ position: 'relative' }}>
          <div
            style={styles.userInfo}
            onClick={() => setMenuOpen(o => !o)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setMenuOpen(o => !o)}
          >
            <div style={styles.avatar}>
              {(currentUser || 'U').charAt(0).toUpperCase()}
            </div>
            <span style={styles.username}>{currentUser || '用户'}</span>
            <span style={{ fontSize: '8px', color: 'var(--text-tertiary)', marginLeft: '2px' }}>▼</span>
          </div>

          {menuOpen && (
            <div style={styles.dropdown}>
              {/* 当前用户 */}
              <div style={styles.dropdownHeader}>
                <span style={styles.dropdownLabel}>切换用户</span>
              </div>

              {switchableUsers?.map((user) => {
                const isActive = currentUser === user.userId || currentUser === user.label
                return (
                  <div
                    key={user.userId}
                    style={{
                      ...styles.menuItem,
                      ...(isActive ? styles.menuItemActive : {}),
                      ...(switching ? { opacity: 0.6, cursor: 'wait' } : {}),
                    }}
                    onClick={() => !switching && !isActive && handleSwitch(user.userId, user.password)}
                  >
                    <div style={styles.menuItemLeft}>
                      <div style={styles.menuAvatar}>
                        {user.label.charAt(0)}
                      </div>
                      <div>
                        <div style={styles.menuName}>{user.label}</div>
                        <div style={styles.menuRole}>{user.role}</div>
                      </div>
                    </div>
                    {isActive && <span style={styles.checkmark}>✓</span>}
                  </div>
                )
              })}

              <div style={styles.divider} />

              {/* 查看个人信息 */}
              <div style={styles.menuItem} onClick={() => { onUserClick?.(); setMenuOpen(false) }}>
                <span style={styles.menuIcon}>👤</span>
                <span>个人信息</span>
              </div>

              {/* 退出登录 */}
              <div style={{ ...styles.menuItem, color: 'var(--status-error)' }} onClick={onLogout}>
                <span style={styles.menuIcon}>⏻</span>
                <span>退出登录</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

const styles: Record<string, any> = {
  topbar: {
    height: '56px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 24px',
    backgroundColor: 'var(--surface-primary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  left: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
  },
  title: {
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  description: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: 'var(--radius-md)',
    transition: 'background-color var(--transition-fast)',
  },
  avatar: {
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: '50%',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  username: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  // Dropdown
  dropdown: {
    position: 'absolute' as const,
    top: 'calc(100% + 6px)',
    right: 0,
    width: '220px',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '10px',
    boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
    zIndex: 1000,
    overflow: 'hidden',
  },
  dropdownHeader: {
    padding: '10px 14px 6px',
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  dropdownLabel: {},
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '10px',
    padding: '8px 14px',
    cursor: 'pointer',
    fontSize: '13px',
    color: 'var(--text-primary)',
    transition: 'background-color 0.15s',
  },
  menuItemActive: {
    backgroundColor: 'var(--surface-secondary)',
  },
  menuItemLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  menuAvatar: {
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: '50%',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    flexShrink: 0,
  },
  menuName: {
    fontSize: '13px',
    fontWeight: 500,
    lineHeight: '1.3',
  },
  menuRole: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  checkmark: {
    fontSize: '14px',
    color: 'var(--status-success)',
    fontWeight: 700,
  },
  menuIcon: {
    fontSize: '14px',
    width: '20px',
    textAlign: 'center' as const,
  },
  divider: {
    height: '1px',
    backgroundColor: 'var(--border-subtle)',
    margin: '4px 0',
  },
}

export default Topbar
