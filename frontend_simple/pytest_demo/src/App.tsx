import { useState } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import TestCaseList from './components/TestCaseList'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import './App.css'

type PageType = 'testCases' | 'agents' | 'tasks'

const navItems: { key: PageType; label: string; icon: string }[] = [
  { key: 'testCases', label: '测试用例', icon: '⬡' },
  { key: 'agents', label: '执行代理', icon: '◉' },
  { key: 'tasks', label: '执行任务', icon: '▸' },
]

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const token = localStorage.getItem('jwt_token')
    if (token) {
      api.setToken(token)
      return true
    }
    return false
  })

  const [currentPage, setCurrentPage] = useState<PageType>('testCases')

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    api.clearToken()
    setIsAuthenticated(false)
  }

  return (
    <div style={styles.app}>
      {isAuthenticated ? (
        <>
          <nav style={styles.navbar}>
            <div style={styles.navbarInner}>
              <div style={styles.brandSection}>
                <div style={styles.logo}>
                  <span style={styles.logoIcon}>⬢</span>
                  <span style={styles.logoText}>TestHub</span>
                </div>
                <div style={styles.navDivider} />
                <div style={styles.navLinks}>
                  {navItems.map((item) => (
                    <button
                      key={item.key}
                      style={{
                        ...styles.navLink,
                        ...(currentPage === item.key ? styles.navLinkActive : {}),
                      }}
                      onClick={() => setCurrentPage(item.key)}
                    >
                      <span style={styles.navIcon}>{item.icon}</span>
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div style={styles.userSection}>
                <button style={styles.logoutBtn} onClick={handleLogout}>
                  <span style={styles.logoutIcon}>⎋</span>
                  退出
                </button>
              </div>
            </div>
          </nav>
          <main style={styles.main}>
            {currentPage === 'testCases' ? (
              <TestCaseList onLogout={handleLogout} />
            ) : currentPage === 'agents' ? (
              <AgentList onLogout={handleLogout} />
            ) : (
              <TaskList onLogout={handleLogout} />
            )}
          </main>
        </>
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </div>
  )
}

const styles = {
  app: {
    minHeight: '100vh',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  navbar: {
    position: 'sticky',
    top: 0,
    zIndex: 100,
    backgroundColor: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-default)',
    backdropFilter: 'blur(12px)',
  } as const,
  navbarInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 24px',
    height: '64px',
  } as const,
  brandSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  } as const,
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  } as const,
  logoIcon: {
    fontSize: '24px',
    color: 'var(--accent-cyan)',
    filter: 'drop-shadow(0 0 8px rgba(57, 208, 214, 0.5))',
  } as const,
  logoText: {
    fontSize: '20px',
    fontWeight: 700,
    letterSpacing: '-0.5px',
    background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text',
  } as const,
  navDivider: {
    width: '1px',
    height: '24px',
    backgroundColor: 'var(--border-default)',
  } as const,
  navLinks: {
    display: 'flex',
    gap: '4px',
  } as const,
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
    cursor: 'pointer',
    border: 'none',
  } as const,
  navLinkActive: {
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  navIcon: {
    fontSize: '16px',
    opacity: 0.8,
  } as const,
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  } as const,
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-default)',
    transition: 'all var(--transition-fast)',
    cursor: 'pointer',
  } as const,
  logoutIcon: {
    fontSize: '14px',
  } as const,
  main: {
    minHeight: 'calc(100vh - 64px)',
    animation: 'fadeIn 0.3s ease',
  } as const,
}

export default App