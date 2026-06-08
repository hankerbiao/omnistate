import { useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import RequirementsPage from './components/RequirementsPage'
import { TestCaseBoardPage } from './components/TestCaseBoard'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import TerminalPage from './components/TerminalPage'
import RoleManagement from './components/RoleManagement'
import UserManagement from './components/UserManagement'
import ProfilePage from './components/ProfilePage'
import MyTasksPage from './components/MyTasksPage'
import PermissionManagement from './components/PermissionManagement'
import DashboardPage from './components/DashboardPage'
import CatalogLabsPage from './components/CatalogLabsPage'
import TestExecutionPlan from './components/TestExecutionPlan'
import LineageViewPage from './components/lineage/LineageViewPage'
import FailureAnalysisPage from './components/failure-analysis/FailureAnalysisPage'
import TraceabilityMatrixPage from './components/TraceabilityMatrixPage'
import { SWITCHABLE_USERS } from './config/users'
import type { WorkflowNavigateTarget } from './components/workflow'
import type { PageType, NavItem, NavSection } from './types/app'
import './App.css'

const navItems: NavItem[] = [
  { key: 'dashboard', label: '数据统计', icon: '◫', permission: 'nav:dashboard:view' },
  { key: 'myTasks', label: '我的任务', icon: '☰' },
  { key: 'requirements', label: '测试需求', icon: '▣' },
  { key: 'traceability', label: '追溯矩阵', icon: '⊞' },
  { key: 'testCases', label: '用例看板', icon: '⚡' },
  { key: 'agents', label: '执行代理', icon: '◉' },
  { key: 'tasks', label: '执行任务', icon: '▶' },
  { key: 'terminal', label: '终端调试', icon: '⎇' },
  { key: 'testPlanStudio', label: '执行计划', icon: '🎯' },
  { key: 'failureAnalysis', label: '失效分析', icon: '⚡', permission: 'execution_tasks:read' },
  { key: 'users', label: '用户管理', icon: '⊕', permission: 'users:read' },
  { key: 'roles', label: '角色管理', icon: '⊞', permission: 'roles:read' },
  { key: 'permissions', label: '权限管理', icon: '◈', permission: 'permissions:read' },
  { key: 'catalogLabs', label: 'Lab 管理', icon: '⊟', permission: 'catalog:labs:manage' },
]

const navSections: NavSection[] = [
  { label: '概览', keys: ['myTasks'] },
  { label: '测试资产', keys: ['requirements', 'traceability', 'testCases'] },
  { label: '执行', keys: ['agents', 'tasks', 'testPlanStudio', 'failureAnalysis', 'terminal'] },
  { label: '系统', keys: ['dashboard', 'users', 'roles', 'permissions', 'catalogLabs'] },
]

function getVisibleNavItems(userPermissions: string[]): NavItem[] {
  return navItems.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission) || userPermissions.some(p => p.startsWith('roles:'))
  })
}

function resolveDefaultPage(visibleItems: NavItem[]): PageType {
  if (visibleItems.some(item => item.key === 'dashboard')) return 'dashboard'
  if (visibleItems.some(item => item.key === 'myTasks')) return 'myTasks'
  return visibleItems[0]?.key ?? 'profile'
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const token = localStorage.getItem('jwt_token')
    if (token) {
      api.setToken(token)
      return true
    }
    return false
  })

  const [currentPage, setCurrentPage] = useState<PageType>('myTasks')
  const initialPageSetRef = useRef(false)
  const [userPermissions, setUserPermissions] = useState<string[]>([])
  const [currentUsername, setCurrentUsername] = useState<string>('')
  const [currentUserId, setCurrentUserId] = useState<string>('')
  const [currentUserRole, setCurrentUserRole] = useState<string>('')
  const [listFilters, setListFilters] = useState<{ requirements?: string }>({})
  const [lineageEntityType, setLineageEntityType] = useState<string>('')
  const [lineageEntityId, setLineageEntityId] = useState<string>('')

  const handleWorkflowNavigate = useCallback((target: WorkflowNavigateTarget) => {
    if (target.page === 'requirements') {
      setListFilters((prev) => ({ ...prev, requirements: target.status }))
    }
    setCurrentPage(target.page)
  }, [])

  const handleOpenLineage = useCallback((type: string, id: string) => {
    setLineageEntityType(type)
    setLineageEntityId(id)
    setCurrentPage('lineageView')
  }, [])

  const resolveUserRole = (userId: string) =>
    SWITCHABLE_USERS.find((u) => u.userId === userId)?.label || userId

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
            setCurrentUserRole(resolveUserRole(userRes.data.user_id))
          }
        } catch (err) {
          console.error('Failed to restore current user:', err)
          api.clearToken()
          setIsAuthenticated(false)
          setUserPermissions([])
          setCurrentUsername('')
          setCurrentUserId('')
          setCurrentUserRole('')
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
        setCurrentUserRole(resolveUserRole(userRes.data.user_id))
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
    setCurrentUserRole('')
    initialPageSetRef.current = false
    setCurrentPage('myTasks')
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
        setCurrentUserRole(resolveUserRole(userRes.data.user_id))
      } else {
        setCurrentUserId(userId)
        setCurrentUserRole(resolveUserRole(userId))
      }
      const permRes = await api.getCurrentUserPermissions()
      setUserPermissions(permRes.data?.permissions || [])
    } catch (err) {
      console.error('Switch user failed:', err)
    }
  }, [])

  const visibleNavItems = getVisibleNavItems(userPermissions)

  useEffect(() => {
    if (!isAuthenticated) {
      initialPageSetRef.current = false
      return
    }
    if (userPermissions.length === 0) return

    const visible = getVisibleNavItems(userPermissions)
    const visibleKeys = new Set(visible.map(item => item.key))

    if (!initialPageSetRef.current) {
      setCurrentPage(resolveDefaultPage(visible))
      initialPageSetRef.current = true
      return
    }

    if (currentPage !== 'profile' && !visibleKeys.has(currentPage)) {
      setCurrentPage(resolveDefaultPage(visible))
    }
  }, [userPermissions, isAuthenticated, currentPage])

  // ─── Page rendering ──────────────────────────────────────────────────
  // 使用工厂函数映射代替长三元表达式链，提升可读性和可维护性
  const renderPage = useCallback((page: PageType): ReactNode => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage key={currentUserId} onWorkflowNavigate={handleWorkflowNavigate} />
      case 'profile':
        return <ProfilePage key={currentUserId} />
      case 'myTasks':
        return <MyTasksPage key={currentUserId} userId={currentUserId} />
      case 'testCases':
        return <TestCaseBoardPage key={currentUserId} />
      case 'requirements':
        return (
          <RequirementsPage
            key={`req-${currentUserId}-${listFilters.requirements ?? ''}`}
            initialStatusFilter={listFilters.requirements}
          />
        )
      case 'traceability':
        return <TraceabilityMatrixPage key={currentUserId} />
      case 'agents':
        return <AgentList key={currentUserId} onLogout={handleLogout} />
      case 'terminal':
        return <TerminalPage key={currentUserId} />
      case 'users':
        return <UserManagement key={currentUserId} />
      case 'roles':
        return <RoleManagement key={currentUserId} />
      case 'permissions':
        return <PermissionManagement key={currentUserId} />
      case 'catalogLabs':
        return <CatalogLabsPage key={currentUserId} />
      case 'testPlanStudio':
        return <TestExecutionPlan key={currentUserId} />
      case 'failureAnalysis':
        return <FailureAnalysisPage key={currentUserId} />
      case 'lineageView':
        return (
          <LineageViewPage
            key={`${currentUserId}-${lineageEntityId}`}
            entityType={lineageEntityType}
            entityId={lineageEntityId}
          />
        )
      case 'tasks':
        return <TaskList key={currentUserId} onLogout={handleLogout} />
      case 'manualTestCases':
        return <TaskList key={currentUserId} onLogout={handleLogout} />
      default:
        return <TaskList key={currentUserId} onLogout={handleLogout} />
    }
  }, [currentUserId, handleWorkflowNavigate, handleLogout, listFilters.requirements, lineageEntityType, lineageEntityId])

  return (
    <>
      {isAuthenticated ? (
        <AppShell
          currentPage={currentPage}
          onNavigate={setCurrentPage}
          visibleNavItems={visibleNavItems}
          navSections={navSections}
          onLogout={handleLogout}
          currentUser={currentUsername}
          currentUserId={currentUserId}
          currentUserRole={currentUserRole}
          onUserClick={() => setCurrentPage('profile')}
          onSwitchUser={handleSwitchUser}
          switchableUsers={SWITCHABLE_USERS}
        >
          {renderPage(currentPage)}
        </AppShell>
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </>
  )
}

export default App
