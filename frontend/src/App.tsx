import { useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { api } from './services/api'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import RequirementsPage from './components/RequirementsPage'
import { TestCaseBoardPage } from './components/TestCaseBoard'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import RoleManagement from './components/RoleManagement'
import UserManagement from './components/UserManagement'
import ProfilePage from './components/ProfilePage'
import MyTasksPage from './components/MyTasksPage'
import PermissionManagement from './components/PermissionManagement'
import DashboardPage from './components/DashboardPage'
import CatalogLabsPage from './components/CatalogLabsPage'
import TestExecutionPlan from './components/TestExecutionPlan'
import LineageViewPage from './components/lineage/LineageViewPage'
import SearchResultsPage from './components/SearchResultsPage'
import TestCaseCollectionPage from './components/TestCaseCollectionPage'
import { SWITCHABLE_USERS } from './config/users'
import { navItems, navSections, getVisibleNavItems, resolveDefaultPage } from './config/navigation'
import type { WorkflowNavigateTarget } from './components/workflow'
import type { PageType } from './types/app'
import './App.css'

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

  const clearUserState = useCallback(() => {
    setCurrentUsername('')
    setCurrentUserId('')
    setCurrentUserRole('')
    setUserPermissions([])
  }, [])

  const setUserInfoFromResponse = useCallback((data: { username?: string; user_id?: string }) => {
    if (data.username) {
      setCurrentUsername(data.username)
    } else if (data.user_id) {
      setCurrentUsername(data.user_id)
    }
    if (data.user_id) {
      setCurrentUserId(data.user_id)
      setCurrentUserRole(resolveUserRole(data.user_id))
    }
  }, [])

  const fetchUserPermissions = useCallback(async () => {
    try {
      const response = await api.getCurrentUserPermissions()
      setUserPermissions(response.data?.permissions || [])
    } catch (err) {
      console.error('Failed to fetch user permissions:', err)
      setUserPermissions([])
    }
  }, [])

  const fetchAndSetCurrentUser = useCallback(async (): Promise<boolean> => {
    try {
      const userRes = await api.getCurrentUser()
      if (userRes.data) setUserInfoFromResponse(userRes.data)
      return true
    } catch (err) {
      console.error('Failed to fetch current user:', err)
      return false
    }
  }, [setUserInfoFromResponse])

  // 应用启动时（页面刷新或首次加载），从 token 恢复用户信息
  useEffect(() => {
    if (isAuthenticated && !currentUserId) {
      (async () => {
        const ok = await fetchAndSetCurrentUser()
        if (!ok) {
          api.clearToken()
          setIsAuthenticated(false)
          clearUserState()
          return
        }
        fetchUserPermissions()
      })()
    }
  }, [isAuthenticated, currentUserId, fetchAndSetCurrentUser, clearUserState, fetchUserPermissions])

  const handleLoginSuccess = async () => {
    setIsAuthenticated(true)
    await fetchAndSetCurrentUser()
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
      const ok = await fetchAndSetCurrentUser()
      if (!ok) throw new Error('获取用户信息失败')
      const permRes = await api.getCurrentUserPermissions()
      setUserPermissions(permRes.data?.permissions || [])
    } catch (err) {
      console.error('Switch user failed:', err)
    }
  }, [fetchAndSetCurrentUser])

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
      case 'search':
        return <SearchResultsPage key={currentUserId} onNavigate={setCurrentPage as (page: string) => void} />
      case 'collections':
        return <TestCaseCollectionPage key={currentUserId} />
      case 'agents':
        return <AgentList key={currentUserId} onLogout={handleLogout} />
      case 'users':
        return <UserManagement key={currentUserId} onNavigate={setCurrentPage} />
      case 'roles':
        return <RoleManagement key={currentUserId} onNavigate={setCurrentPage} />
      case 'permissions':
        return <PermissionManagement key={currentUserId} />
      case 'catalogLabs':
        return <CatalogLabsPage key={currentUserId} />
      case 'testPlanStudio':
        return <TestExecutionPlan key={currentUserId} />
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
          onSearchNavigate={setCurrentPage as (page: string) => void}
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
