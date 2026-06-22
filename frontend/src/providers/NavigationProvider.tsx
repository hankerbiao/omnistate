import { createContext, useContext, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import { navSections, getVisibleNavItemsWithIcons, resolveDefaultPage } from '../config/navigation'
import type { NavItemWithIcon, NavSection, PageType } from '../types/app'
import { PAGE_ROUTES, ROUTE_TO_PAGE } from '../router/routes'

export interface WorkflowNavigateTarget {
  page: 'requirements' | 'manualTestCases' | 'myTasks'
  status?: string
}

interface NavigationContextType {
  currentPage: PageType
  navigate: (page: PageType) => void
  visibleNavItems: NavItemWithIcon[]
  navSections: NavSection[]
  requirementsFilter?: string
  lineageEntityType: string
  lineageEntityId: string
  handleWorkflowNavigate: (target: WorkflowNavigateTarget) => void
  handleOpenLineage: (type: string, id: string) => void
}

const NavigationContext = createContext<NavigationContextType | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useNavigation(): NavigationContextType {
  const ctx = useContext(NavigationContext)
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider')
  return ctx
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, userPermissions } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const visibleNavItems = getVisibleNavItemsWithIcons(userPermissions)

  // Derive currentPage from URL path
  const currentPage: PageType = ROUTE_TO_PAGE[location.pathname] ?? 'myTasks'

  // Use ref to store mutable navigation state (requirementsFilter, lineage) without re-renders
  const requirementsFilterRef = useRef<string | undefined>(undefined)
  const lineageStateRef = useRef<{ type: string; id: string }>({ type: '', id: '' })
  const initialRedirectRef = useRef(false)

  const handleNavigate = useCallback((page: PageType) => {
    const path = PAGE_ROUTES[page]
    if (path) navigate(path)
  }, [navigate])

  const handleWorkflowNavigate = useCallback((target: WorkflowNavigateTarget) => {
    if (target.page === 'requirements') {
      requirementsFilterRef.current = target.status
    }
    const path = PAGE_ROUTES[target.page]
    if (path) navigate(path)
  }, [navigate])

  const handleOpenLineage = useCallback((type: string, id: string) => {
    lineageStateRef.current = { type, id }
    navigate(PAGE_ROUTES.lineageView)
  }, [navigate])

  // On login: redirect to default page based on permissions
  useEffect(() => {
    if (!isAuthenticated || userPermissions.length === 0) return
    if (initialRedirectRef.current) return

    const visible = getVisibleNavItemsWithIcons(userPermissions)
    const visibleKeys = new Set(visible.map(item => item.key))
    const currentPathPage = ROUTE_TO_PAGE[location.pathname]

    // If on root or page not in visible items, redirect to default
    if (!currentPathPage || (currentPathPage !== 'profile' && !visibleKeys.has(currentPathPage))) {
      const defaultPage = resolveDefaultPage(visible)
      navigate(PAGE_ROUTES[defaultPage], { replace: true })
    }

    initialRedirectRef.current = true
  }, [isAuthenticated, userPermissions, location.pathname, navigate])

  // Reset on logout
  useEffect(() => {
    if (!isAuthenticated) {
      initialRedirectRef.current = false
      requirementsFilterRef.current = undefined
      lineageStateRef.current = { type: '', id: '' }
    }
  }, [isAuthenticated])

  return (
    <NavigationContext.Provider
      value={{
        currentPage,
        navigate: handleNavigate,
        visibleNavItems,
        navSections,
        requirementsFilter: requirementsFilterRef.current,
        lineageEntityType: lineageStateRef.current.type,
        lineageEntityId: lineageStateRef.current.id,
        handleWorkflowNavigate,
        handleOpenLineage,
      }}
    >
      {children}
    </NavigationContext.Provider>
  )
}
