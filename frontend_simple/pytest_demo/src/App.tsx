import { useState } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import TestCaseList from './components/TestCaseList'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import './App.css'

type PageType = 'testCases' | 'agents' | 'tasks'

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
    <>
      {isAuthenticated ? (
        <div>
          <nav style={styles.navbar}>
            <div style={styles.navbarContainer}>
              <div style={styles.navbarBrand}>测试管理平台</div>
              <div style={styles.navbarLinks}>
                <button
                  style={{
                    ...styles.navbarLink,
                    ...(currentPage === 'testCases' ? styles.navbarLinkActive : {}),
                  }}
                  onClick={() => setCurrentPage('testCases')}
                >
                  测试用例
                </button>
                <button
                  style={{
                    ...styles.navbarLink,
                    ...(currentPage === 'agents' ? styles.navbarLinkActive : {}),
                  }}
                  onClick={() => setCurrentPage('agents')}
                >
                  执行代理
                </button>
                <button
                  style={{
                    ...styles.navbarLink,
                    ...(currentPage === 'tasks' ? styles.navbarLinkActive : {}),
                  }}
                  onClick={() => setCurrentPage('tasks')}
                >
                  执行任务
                </button>
              </div>
            </div>
          </nav>
          {currentPage === 'testCases' ? (
            <TestCaseList onLogout={handleLogout} />
          ) : currentPage === 'agents' ? (
            <AgentList onLogout={handleLogout} />
          ) : (
            <TaskList onLogout={handleLogout} />
          )}
        </div>
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  )
}

const styles = {
  navbar: {
    backgroundColor: '#343a40',
    color: '#fff',
    padding: '0',
    marginBottom: '20px',
  } as const,
  navbarContainer: {
    maxWidth: '1600px',
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 20px',
    height: '60px',
  } as const,
  navbarBrand: {
    fontSize: '20px',
    fontWeight: 'bold',
  } as const,
  navbarLinks: {
    display: 'flex',
    gap: '10px',
  } as const,
  navbarLink: {
    backgroundColor: 'transparent',
    color: '#adb5bd',
    border: 'none',
    padding: '10px 20px',
    fontSize: '14px',
    cursor: 'pointer',
    borderRadius: '4px',
    transition: 'all 0.2s',
  } as const,
  navbarLinkActive: {
    backgroundColor: '#007bff',
    color: '#fff',
  } as const,
}

export default App
