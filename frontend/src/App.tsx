import { useState } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import RequirementsPage from './components/RequirementsPage'
import TestCaseList from './components/TestCaseList'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import TerminalPage from './components/TerminalPage'
import RoleManagement from './components/RoleManagement'
import UserManagement from './components/UserManagement'
import type { PageType, NavItem } from './types/app'
import './App.css'

const navItems: NavItem[] = [
  { key: 'requirements', label: '测试需求', icon: '▣' },
  { key: 'testCases', label: '自动化用例', icon: '⚡' },
  { key: 'agents', label: '执行代理', icon: '◉' },
  { key: 'tasks', label: '执行任务', icon: '▸' },
  { key: 'terminal', label: '终端调试', icon: '⌘' },
  { key: 'users', label: '用户管理', icon: '👤', permission: 'users:read' },
  { key: 'roles', label: '角色管理', icon: '👥', permission: 'roles:read' },
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

  const [currentPage, setCurrentPage] = useState<PageType>('requirements')
  const [userPermissions, setUserPermissions] = useState<string[]>([])
  const [currentUsername, setCurrentUsername] = useState<string>('')

  const fetchUserPermissions = async () => {
    try {
      const response = await api.getCurrentUserPermissions()
      setUserPermissions(response.data?.permissions || [])
    } catch (err) {
      console.error('Failed to fetch user permissions:', err)
      setUserPermissions([])
    }
  }

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
    fetchUserPermissions()
  }

  const handleLogout = () => {
    api.clearToken()
    setIsAuthenticated(false)
    setUserPermissions([])
    setCurrentUsername('')
  }

  const visibleNavItems = navItems.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission) || userPermissions.some(p => p.startsWith('roles:'))
  })

  return (
    <>
      {isAuthenticated ? (
        <AppShell
          currentPage={currentPage}
          onNavigate={setCurrentPage}
          visibleNavItems={visibleNavItems}
          onLogout={handleLogout}
          currentUser={currentUsername}
        >
          {currentPage === 'testCases' ? (
            <TestCaseList />
          ) : currentPage === 'requirements' ? (
            <RequirementsPage />
          ) : currentPage === 'agents' ? (
            <AgentList onLogout={handleLogout} />
          ) : currentPage === 'terminal' ? (
            <TerminalPage />
          ) : currentPage === 'users' ? (
            <UserManagement />
          ) : currentPage === 'roles' ? (
            <RoleManagement />
          ) : (
            <TaskList onLogout={handleLogout} />
          )}
        </AppShell>
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  )
}

export default App