import { useState, useCallback, useEffect } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import RequirementsPage from './components/RequirementsPage'
import TestCaseList from './components/TestCaseList'
import ManualTestCaseList from './components/ManualTestCaseList'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import TerminalPage from './components/TerminalPage'
import RoleManagement from './components/RoleManagement'
import UserManagement from './components/UserManagement'
import ProfilePage from './components/ProfilePage'
import MyTasksPage from './components/MyTasksPage'
import PermissionManagement from './components/PermissionManagement'
import DashboardPage from './components/DashboardPage'
import { SWITCHABLE_USERS } from './config/users'
import type { PageType, NavItem } from './types/app'
import './App.css'

const navItems: NavItem[] = [
  { key: 'dashboard', label: '数据统计', icon: '📊' },
  { key: 'myTasks', label: '我的任务', icon: '☰' },
  { key: 'requirements', label: '测试需求', icon: '▣' },
  { key: 'manualTestCases', label: '测试用例', icon: '📋' },
  { key: 'testCases', label: '自动化用例', icon: '⚡' },
  { key: 'agents', label: '执行代理', icon: '◉' },
  { key: 'tasks', label: '执行任务', icon: '▸' },
  { key: 'terminal', label: '终端调试', icon: '⌘' },
  { key: 'users', label: '用户管理', icon: '👤', permission: 'users:read' },
  { key: 'roles', label: '角色管理', icon: '👥', permission: 'roles:read' },
  { key: 'permissions', label: '权限管理', icon: '🔑', permission: 'permissions:read' },
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
  const [currentUserId, setCurrentUserId] = useState<string>('')

  const fetchUserPermissions = async () => {
    try {
      const response = await api.getCurrentUserPermissions()
      setUserPermissions(response.data?.permissions || [])
    } catch (err) {
      console.error('Failed to fetch user permissions:', err)
      setUserPermissions([])
    }
  }

  // 应用启动时（页面刷新或首次加载），从 token 恢复用户信息
  useEffect(() => {
    if (isAuthenticated && !currentUserId) {
      const initUser = async () => {
        try {
          const userRes = await api.getCurrentUser()
          if (userRes.data?.username) {
            setCurrentUsername(userRes.data.username)
          } else if (userRes.data?.user_id) {
            setCurrentUsername(userRes.data.user_id)
          }
          if (userRes.data?.user_id) {
            setCurrentUserId(userRes.data.user_id)
          }
        } catch (err) {
          console.error('Failed to restore current user:', err)
          api.clearToken()
          setIsAuthenticated(false)
          setUserPermissions([])
          setCurrentUsername('')
          setCurrentUserId('')
          return
        }
        fetchUserPermissions()
      }
      initUser()
    }
  }, [isAuthenticated])

  const handleLoginSuccess = async () => {
    setIsAuthenticated(true)
    // 获取当前用户信息
    try {
      const userRes = await api.getCurrentUser()
      if (userRes.data?.username) {
        setCurrentUsername(userRes.data.username)
      } else if (userRes.data?.user_id) {
        setCurrentUsername(userRes.data.user_id)
      }
      if (userRes.data?.user_id) {
        setCurrentUserId(userRes.data.user_id)
      }
    } catch (err) {
      console.error('Failed to fetch current user:', err)
    }
    fetchUserPermissions()
  }

  const handleLogout = () => {
    api.clearToken()
    setIsAuthenticated(false)
    setUserPermissions([])
    setCurrentUsername('')
    setCurrentUserId('')
  }

  const handleSwitchUser = useCallback(async (userId: string, password: string) => {
    try {
      const loginRes = await api.login({ user_id: userId, password })
      api.setToken(loginRes.data.access_token)
      const userRes = await api.getCurrentUser()
      if (userRes.data?.username) {
        setCurrentUsername(userRes.data.username)
      } else if (userRes.data?.user_id) {
        setCurrentUsername(userRes.data.user_id)
      }
      if (userRes.data?.user_id) {
        setCurrentUserId(userRes.data.user_id)
      }
      const permRes = await api.getCurrentUserPermissions()
      setUserPermissions(permRes.data?.permissions || [])
    } catch (err) {
      console.error('Switch user failed:', err)
    }
  }, [])

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
          onUserClick={() => setCurrentPage('profile')}
          onSwitchUser={handleSwitchUser}
          switchableUsers={SWITCHABLE_USERS}
        >
          {currentPage === 'dashboard' ? (
            <DashboardPage key={currentUserId} />
          ) : currentPage === 'profile' ? (
            <ProfilePage key={currentUserId} />
          ) : currentPage === 'myTasks' ? (
            <MyTasksPage key={currentUserId} userId={currentUserId} />
          ) : currentPage === 'testCases' ? (
            <TestCaseList key={currentUserId} />
          ) : currentPage === 'manualTestCases' ? (
            <ManualTestCaseList key={currentUserId} />
          ) : currentPage === 'requirements' ? (
            <RequirementsPage key={currentUserId} />
          ) : currentPage === 'agents' ? (
            <AgentList key={currentUserId} onLogout={handleLogout} />
          ) : currentPage === 'terminal' ? (
            <TerminalPage key={currentUserId} />
          ) : currentPage === 'users' ? (
            <UserManagement key={currentUserId} />
          ) : currentPage === 'roles' ? (
            <RoleManagement key={currentUserId} />
          ) : currentPage === 'permissions' ? (
            <PermissionManagement key={currentUserId} />
          ) : (
            <TaskList key={currentUserId} onLogout={handleLogout} />
          )}
        </AppShell>
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  )
}

export default App