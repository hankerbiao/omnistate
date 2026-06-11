import { useCallback, type ReactNode } from 'react'
import { AuthProvider, useAuth } from './providers/AuthProvider'
import { NavigationProvider, useNavigation } from './providers/NavigationProvider'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import RequirementsPage from './components/RequirementsPage'
import { TestCaseBoardPage } from './components/TestCaseBoard'
import AgentList from './components/AgentList'
import TaskList from './components/TaskList'
import RoleManagement from './components/RoleManagement'
import RoleGroupManagement from './components/RoleGroupManagement'
import UserManagement from './components/UserManagement'
import ProfilePage from './components/ProfilePage'
import MyTasksPage from './components/MyTasksPage'
import PermissionManagement from './components/PermissionManagement'
import DashboardPage from './components/DashboardPage'
import CatalogLabsPage from './components/CatalogLabsPage'
import TestExecutionPlanDemo from './components/TestExecutionPlanDemo'
import LineageViewPage from './components/lineage/LineageViewPage'
import TestCaseCollectionPage from './components/TestCaseCollectionPage'
import SystemConfigPage from './pages/SystemConfig'
import SearchPage from './pages/SearchPage'
import type { PageType } from './types/app'
import './App.css'

function AppContent() {
  const { isAuthenticated, currentUserId, handleLoginSuccess, handleLogout } = useAuth()
  const { currentPage, navigate, requirementsFilter, lineageEntityType, lineageEntityId, handleWorkflowNavigate } = useNavigation()

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
            key={`req-${currentUserId}-${requirementsFilter ?? ''}`}
            initialStatusFilter={requirementsFilter}
          />
        )
      case 'collections':
        return <TestCaseCollectionPage key={currentUserId} currentUserId={currentUserId} />
      case 'search':
        return <SearchPage key={currentUserId} onNavigate={navigate as (page: string) => void} />
      case 'systemConfig':
        return <SystemConfigPage key={currentUserId} />
      case 'agents':
        return <AgentList key={currentUserId} onLogout={handleLogout} />
      case 'users':
        return <UserManagement key={currentUserId} onNavigate={navigate} />
      case 'roles':
        return <RoleManagement key={currentUserId} onNavigate={navigate} />
      case 'roleGroup':
        return <RoleGroupManagement key={currentUserId} onNavigate={navigate} />
      case 'permissions':
        return <PermissionManagement key={currentUserId} />
      case 'catalogLabs':
        return <CatalogLabsPage key={currentUserId} />
      case 'testPlanStudioDemo':
        return <TestExecutionPlanDemo key={currentUserId} />
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
  }, [currentUserId, handleWorkflowNavigate, handleLogout, navigate, requirementsFilter, lineageEntityType, lineageEntityId])

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <AppShell>
      {renderPage(currentPage)}
    </AppShell>
  )
}

function App() {
  return (
    <AuthProvider>
      <NavigationProvider>
        <AppContent />
      </NavigationProvider>
    </AuthProvider>
  )
}

export default App
