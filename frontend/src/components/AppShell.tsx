import Sidebar from './Sidebar'
import Topbar from './Topbar'
import type { PageType, NavItem } from '../types/app'

const PAGE_TITLES: Record<PageType, { title: string; description?: string }> = {
  requirements: { title: '测试需求', description: '管理和跟踪测试需求' },
  manualTestCases: { title: '测试用例', description: '查看和管理手工测试用例' },
  testCases: { title: '自动化用例', description: '查看和管理自动化测试用例' },
  duts: { title: 'DUT 管理', description: '管理测试机器信息' },
  agents: { title: '执行代理', description: '监控代理运行状态' },
  tasks: { title: '执行任务', description: '下发和管理测试任务' },
  terminal: { title: '终端调试', description: '开发调试工具' },
  users: { title: '用户管理', description: '管理系统用户和权限' },
  roles: { title: '角色管理', description: '配置角色和权限' },
  profile: { title: '个人信息', description: '查看个人信息和权限' },
}

interface AppShellProps {
  children: React.ReactNode
  currentPage: PageType
  onNavigate: (page: PageType) => void
  visibleNavItems: NavItem[]
  onLogout: () => void
  currentUser?: string
  onUserClick?: () => void
}

const AppShell: React.FC<AppShellProps> = ({
  children,
  currentPage,
  onNavigate,
  visibleNavItems,
  onLogout,
  currentUser,
  onUserClick,
}) => {
  const pageInfo = PAGE_TITLES[currentPage] || { title: 'TestHub' }

  return (
    <div style={styles.shell}>
      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        visibleItems={visibleNavItems}
      />
      <div style={styles.main}>
        <Topbar
          title={pageInfo.title}
          description={pageInfo.description}
          onLogout={onLogout}
          currentUser={currentUser}
          onUserClick={onUserClick}
        />
        <main style={styles.workspace}>
          {children}
        </main>
      </div>
    </div>
  )
}

const styles = {
  shell: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  workspace: {
    flex: 1,
    overflow: 'auto',
    backgroundColor: 'var(--surface-secondary)',
  },
}

export default AppShell