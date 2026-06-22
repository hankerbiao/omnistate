import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './providers/AuthProvider'
import { NavigationProvider, useNavigation } from './providers/NavigationProvider'
import LoginPage from './components/LoginPage'
import AppShell from './components/AppShell'
import { PAGE_ROUTES } from './router/routes'
import './App.css'

// Lazy-loaded page components (route-level code splitting)
const DashboardPage = lazy(() => import('./components/DashboardPage'))
const MyTasksPage = lazy(() => import('./components/MyTasksPage'))
const TestCaseBoardPage = lazy(() => import('./components/TestCaseBoard').then(m => ({ default: m.TestCaseBoardPage })))
const RequirementsPage = lazy(() => import('./components/RequirementsPage'))
const TestCaseCollectionPage = lazy(() => import('./components/TestCaseCollectionPage'))
const ProjectsPage = lazy(() => import('./components/ProjectsPage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const SystemConfigPage = lazy(() => import('./pages/SystemConfig'))
const AgentList = lazy(() => import('./components/AgentList'))
const UserManagement = lazy(() => import('./components/UserManagement'))
const RoleManagement = lazy(() => import('./components/RoleManagement'))
const RoleGroupManagement = lazy(() => import('./components/RoleGroupManagement'))
const PermissionManagement = lazy(() => import('./components/PermissionManagement'))
const CatalogLabsPage = lazy(() => import('./components/CatalogLabsPage'))
const CaseGovernancePage = lazy(() => import('./components/CaseGovernancePage'))
const TestExecutionPlanDemo = lazy(() => import('./components/TestExecutionPlanDemo'))
const ProfilePage = lazy(() => import('./components/ProfilePage'))
const LineageViewPage = lazy(() => import('./components/lineage/LineageViewPage'))

function PageLoading() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px' }}>
      <div style={{ color: 'var(--text-tertiary)', fontSize: '14px' }}>加载中...</div>
    </div>
  )
}

/**
 * Layout route: wraps all authenticated pages with AppShell + Suspense.
 * <Outlet /> renders the matched child route element.
 */
function AuthenticatedLayout() {
  return (
    <AppShell>
      <Suspense fallback={<PageLoading />}>
        <Outlet />
      </Suspense>
    </AppShell>
  )
}

/** Route wrapper components: only created when route matches */
function DashboardRoute() {
  const { currentUserId } = useAuth()
  const { handleWorkflowNavigate } = useNavigation()
  return <DashboardPage key={currentUserId} onWorkflowNavigate={handleWorkflowNavigate} />
}
function MyTasksRoute() {
  const { currentUserId } = useAuth()
  return <MyTasksPage key={currentUserId} userId={currentUserId} />
}
function TestCaseBoardRoute() {
  const { currentUserId } = useAuth()
  return <TestCaseBoardPage key={currentUserId} />
}
function RequirementsRoute() {
  const { currentUserId } = useAuth()
  const { requirementsFilter } = useNavigation()
  return <RequirementsPage key={`req-${currentUserId}-${requirementsFilter ?? ''}`} initialStatusFilter={requirementsFilter} />
}
function CollectionsRoute() {
  const { currentUserId } = useAuth()
  return <TestCaseCollectionPage key={currentUserId} currentUserId={currentUserId} />
}
function ProjectsRoute() {
  const { currentUserId } = useAuth()
  return <ProjectsPage key={currentUserId} />
}
function SearchRoute() {
  const { currentUserId } = useAuth()
  const { navigate } = useNavigation()
  return <SearchPage key={currentUserId} onNavigate={navigate as (page: string) => void} />
}
function SystemConfigRoute() {
  const { currentUserId } = useAuth()
  return <SystemConfigPage key={currentUserId} />
}
function AgentsRoute() {
  const { currentUserId } = useAuth()
  const { handleLogout } = useAuth()
  return <AgentList key={currentUserId} onLogout={handleLogout} />
}
function UsersRoute() {
  const { currentUserId } = useAuth()
  const { navigate } = useNavigation()
  return <UserManagement key={currentUserId} onNavigate={navigate as (page: string) => void} />
}
function RolesRoute() {
  const { currentUserId } = useAuth()
  const { navigate } = useNavigation()
  return <RoleManagement key={currentUserId} onNavigate={navigate as (page: string) => void} />
}
function RoleGroupRoute() {
  const { currentUserId } = useAuth()
  const { navigate } = useNavigation()
  return <RoleGroupManagement key={currentUserId} onNavigate={navigate as (page: string) => void} />
}
function PermissionsRoute() {
  const { currentUserId } = useAuth()
  return <PermissionManagement key={currentUserId} />
}
function CatalogLabsRoute() {
  const { currentUserId } = useAuth()
  return <CatalogLabsPage key={currentUserId} />
}
function CaseGovernanceRoute() {
  const { currentUserId } = useAuth()
  return <CaseGovernancePage key={currentUserId} />
}
function TestPlanRoute() {
  const { currentUserId } = useAuth()
  return <TestExecutionPlanDemo key={currentUserId} />
}
function ProfileRoute() {
  const { currentUserId } = useAuth()
  return <ProfilePage key={currentUserId} />
}
function LineageRoute() {
  const { currentUserId } = useAuth()
  const { lineageEntityType, lineageEntityId } = useNavigation()
  return <LineageViewPage key={`${currentUserId}-${lineageEntityId}`} entityType={lineageEntityType} entityId={lineageEntityId} />
}

function AppContent() {
  const { isAuthenticated, handleLoginSuccess } = useAuth()

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <Routes>
      <Route element={<AuthenticatedLayout />}>
        <Route path="/" element={<Navigate to={PAGE_ROUTES.myTasks} replace />} />
        <Route path={PAGE_ROUTES.dashboard} element={<DashboardRoute />} />
        <Route path={PAGE_ROUTES.myTasks} element={<MyTasksRoute />} />
        <Route path={PAGE_ROUTES.testCases} element={<TestCaseBoardRoute />} />
        <Route path={PAGE_ROUTES.requirements} element={<RequirementsRoute />} />
        <Route path={PAGE_ROUTES.collections} element={<CollectionsRoute />} />
        <Route path={PAGE_ROUTES.projects} element={<ProjectsRoute />} />
        <Route path={PAGE_ROUTES.search} element={<SearchRoute />} />
        <Route path={PAGE_ROUTES.systemConfig} element={<SystemConfigRoute />} />
        <Route path={PAGE_ROUTES.agents} element={<AgentsRoute />} />
        <Route path={PAGE_ROUTES.users} element={<UsersRoute />} />
        <Route path={PAGE_ROUTES.roles} element={<RolesRoute />} />
        <Route path={PAGE_ROUTES.roleGroup} element={<RoleGroupRoute />} />
        <Route path={PAGE_ROUTES.permissions} element={<PermissionsRoute />} />
        <Route path={PAGE_ROUTES.catalogLabs} element={<CatalogLabsRoute />} />
        <Route path={PAGE_ROUTES.caseGovernance} element={<CaseGovernanceRoute />} />
        <Route path={PAGE_ROUTES.testPlanStudioDemo} element={<TestPlanRoute />} />
        <Route path={PAGE_ROUTES.manualTestCases} element={<TestPlanRoute />} />
        <Route path={PAGE_ROUTES.profile} element={<ProfileRoute />} />
        <Route path={PAGE_ROUTES.lineageView} element={<LineageRoute />} />
        <Route path="*" element={<Navigate to={PAGE_ROUTES.myTasks} replace />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavigationProvider>
          <AppContent />
        </NavigationProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
