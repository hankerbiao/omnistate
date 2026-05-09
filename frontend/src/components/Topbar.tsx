interface TopbarProps {
  title: string
  description?: string
  onLogout: () => void
  currentUser?: string
  onUserClick?: () => void
}

const Topbar: React.FC<TopbarProps> = ({ title, description, onLogout, currentUser, onUserClick }) => {
  return (
    <header style={styles.topbar}>
      <div style={styles.left}>
        <h1 style={styles.title}>{title}</h1>
        {description && (
          <span style={styles.description}>{description}</span>
        )}
      </div>
      <div style={styles.right}>
        <div
          style={styles.userInfo}
          onClick={onUserClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onUserClick?.()}
        >
          <div style={styles.avatar}>
            {(currentUser || 'U').charAt(0).toUpperCase()}
          </div>
          <span style={styles.username}>{currentUser || '用户'}</span>
        </div>
        <button style={styles.logoutBtn} onClick={onLogout}>
          <span style={styles.logoutIcon}>⏻</span>
          退出
        </button>
      </div>
    </header>
  )
}

const styles = {
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
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  },
  logoutIcon: {
    fontSize: '14px',
  },
}

export default Topbar