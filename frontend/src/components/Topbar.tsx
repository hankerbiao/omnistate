import { useState } from 'react'
import { useTheme } from 'next-themes'

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
  onUserClick,
  onSwitchUser,
  switchableUsers,
}) => {
  const [switching, setSwitching] = useState(false)
  const { resolvedTheme, setTheme } = useTheme()

  const isUserActive = (user: SwitchableUser) =>
    currentUserId === user.userId ||
    currentUser === user.userId ||
    currentUser === user.label

  const handleSwitch = async (userId: string, password: string) => {
    if (!onSwitchUser) return
    setSwitching(true)
    try {
      await onSwitchUser(userId, password)
    } finally {
      setSwitching(false)
    }
  }

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, minWidth: 0, flex: '1 1 auto' }}>
        <h1 className="topbar__title">{title}</h1>
        {description && <span className="topbar__desc">{description}</span>}
      </div>

      <div className="topbar__actions">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          title={resolvedTheme === 'dark' ? '切换到明亮模式' : '切换到暗黑模式'}
        >
          {resolvedTheme === 'dark' ? '☀️' : '🌙'}
        </button>

        {switchableUsers && switchableUsers.length > 0 && (
          <div className="topbar__user-switcher" role="group" aria-label="切换用户">
            {switchableUsers.map(user => {
              const isActive = isUserActive(user)
              return (
                <button
                  key={user.userId}
                  type="button"
                  className={`topbar__user-chip${isActive ? ' topbar__user-chip--active' : ''}`}
                  disabled={switching || isActive}
                  aria-current={isActive ? 'true' : undefined}
                  title={`${user.label}（${user.role}）`}
                  onClick={() => handleSwitch(user.userId, user.password)}
                >
                  <span className="topbar__avatar">{user.label.charAt(0)}</span>
                  <span className="topbar__user-chip-label">{user.label}</span>
                  {isActive && <span className="topbar__user-chip-check" aria-hidden="true">✓</span>}
                </button>
              )
            })}
          </div>
        )}

        <div className="topbar__account-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onUserClick?.()}
          >
            个人信息
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm topbar__logout-btn"
            onClick={onLogout}
          >
            退出
          </button>
        </div>
      </div>
    </header>
  )
}

export default Topbar
