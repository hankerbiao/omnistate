import type { PageType, NavItem } from '../types/app'

interface SidebarProps {
  currentPage: PageType
  onNavigate: (page: PageType) => void
  visibleItems: NavItem[]
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate, visibleItems }) => {
  return (
    <aside style={styles.sidebar}>
      {/* Brand */}
      <div style={styles.brand}>
        <div style={styles.brandIcon}>
          <span style={styles.logoText}>TH</span>
        </div>
        <div style={styles.brandText}>
          <span style={styles.appName}>TestHub</span>
          <span style={styles.appVersion}>v1.0</span>
        </div>
      </div>

      {/* Navigation */}
      <nav style={styles.nav}>
        <div style={styles.navSection}>
          <span style={styles.navLabel}>业务模块</span>
          {visibleItems.map(item => (
            <button
              key={item.key}
              style={{
                ...styles.navItem,
                ...(currentPage === item.key ? styles.navItemActive : {}),
              }}
              onClick={() => onNavigate(item.key)}
            >
              <span style={styles.navIcon}>{item.icon}</span>
              <span style={styles.navText}>{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div style={styles.footer}>
        <span style={styles.footerText}>研发运营平台</span>
      </div>
    </aside>
  )
}

const styles = {
  sidebar: {
    width: '240px',
    minWidth: '240px',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--surface-primary)',
    borderRight: '1px solid var(--border-subtle)',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '20px 16px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  brandIcon: {
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--accent-primary)',
    borderRadius: 'var(--radius-md)',
  },
  logoText: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'white',
  },
  brandText: {
    display: 'flex',
    flexDirection: 'column' as const,
  },
  appName: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  appVersion: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  nav: {
    flex: 1,
    padding: '12px 8px',
    overflowY: 'auto' as const,
  },
  navSection: {
    marginBottom: '8px',
  },
  navLabel: {
    display: 'block',
    padding: '8px 12px 6px',
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    width: '100%',
    padding: '10px 12px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
    textAlign: 'left' as const,
  },
  navItemActive: {
    color: 'var(--accent-primary)',
    backgroundColor: 'var(--surface-hover)',
  },
  navIcon: {
    fontSize: '16px',
    width: '20px',
    textAlign: 'center' as const,
  },
  navText: {
    flex: 1,
  },
  footer: {
    padding: '16px',
    borderTop: '1px solid var(--border-subtle)',
    textAlign: 'center' as const,
  },
  footerText: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
}

export default Sidebar