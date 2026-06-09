import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { useAuth } from './AuthProvider';
import { navSections, getVisibleNavItems, resolveDefaultPage } from '../config/navigation';
import type { NavItem, NavSection, PageType } from '../types/app';

export interface WorkflowNavigateTarget {
  page: 'requirements' | 'manualTestCases' | 'myTasks';
  status?: string;
}

interface NavigationContextType {
  currentPage: PageType;
  navigate: (page: PageType) => void;
  visibleNavItems: NavItem[];
  navSections: NavSection[];
  /** 需求列表过滤器（从工作流导航传递） */
  requirementsFilter?: string;
  /** 血缘视图实体类型 */
  lineageEntityType: string;
  /** 血缘视图实体 ID */
  lineageEntityId: string;
  handleWorkflowNavigate: (target: WorkflowNavigateTarget) => void;
  handleOpenLineage: (type: string, id: string) => void;
}

const NavigationContext = createContext<NavigationContextType | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useNavigation(): NavigationContextType {
  const ctx = useContext(NavigationContext);
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider');
  return ctx;
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, userPermissions } = useAuth();

  const [currentPage, setCurrentPage] = useState<PageType>('myTasks');
  const [requirementsFilter, setRequirementsFilter] = useState<string | undefined>(undefined);
  const [lineageEntityType, setLineageEntityType] = useState<string>('');
  const [lineageEntityId, setLineageEntityId] = useState<string>('');
  const initialPageSetRef = useRef(false);

  const visibleNavItems = getVisibleNavItems(userPermissions);

  const navigate = useCallback((page: PageType) => {
    setCurrentPage(page);
  }, []);

  const handleWorkflowNavigate = useCallback((target: WorkflowNavigateTarget) => {
    if (target.page === 'requirements') {
      setRequirementsFilter(target.status);
    }
    setCurrentPage(target.page);
  }, []);

  const handleOpenLineage = useCallback((type: string, id: string) => {
    setLineageEntityType(type);
    setLineageEntityId(id);
    setCurrentPage('lineageView');
  }, []);

  // 登录状态变化时重置导航
  useEffect(() => {
    if (!isAuthenticated) {
      initialPageSetRef.current = false;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCurrentPage('myTasks');
      setRequirementsFilter(undefined);
      setLineageEntityType('');
      setLineageEntityId('');
    }
  }, [isAuthenticated]);

  // 权限加载完成后设置默认页面
  useEffect(() => {
    if (!isAuthenticated) return;
    if (userPermissions.length === 0) return;

    const visible = getVisibleNavItems(userPermissions);
    const visibleKeys = new Set(visible.map((item) => item.key));

    if (!initialPageSetRef.current) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCurrentPage(resolveDefaultPage(visible));
      initialPageSetRef.current = true;
      return;
    }

    if (currentPage !== 'profile' && !visibleKeys.has(currentPage)) {
      setCurrentPage(resolveDefaultPage(visible));
    }
  }, [userPermissions, isAuthenticated, currentPage]);

  return (
    <NavigationContext.Provider
      value={{
        currentPage,
        navigate,
        visibleNavItems,
        navSections,
        requirementsFilter,
        lineageEntityType,
        lineageEntityId,
        handleWorkflowNavigate,
        handleOpenLineage,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
}
