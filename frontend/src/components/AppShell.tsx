import { useAuth } from '../providers/AuthProvider'
import { useNavigation } from '../providers/NavigationProvider'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

const PAGE_TITLES: Record<string, { title: string; description?: string }> = {
  requirements: { title: '测试用例编写需求', description: '管理和跟踪测试用例编写需求' },
  myTasks: { title: '我的任务', description: '待处理的工作项' },
  manualTestCases: { title: '测试用例', description: '查看和管理手工测试用例' },
  testCases: { title: '用例看板', description: '概览、浏览和管理测试用例' },
  agents: { title: '执行代理', description: '监控代理运行状态' },
  users: { title: '用户管理', description: '管理系统用户和权限' },
  roles: { title: '角色管理', description: '配置角色和权限' },
  roleGroup: { title: '用户组管理', description: '管理组成员与权限' },
  profile: { title: '个人信息', description: '查看个人信息和权限' },
  permissions: { title: '权限管理', description: '管理系统权限项' },
  dashboard: { title: '数据统计', description: '测试数据整体概览' },
  catalogLabs: { title: 'Lab 管理', description: '管理测试用例目录 Lab' },
  testPlanStudioDemo: { title: '执行计划(demo)', description: '重构版执行计划页面' },
  caseGovernance: { title: '用例治理', description: '发现并补全不完整的测试用例' },
  projects: { title: '项目', description: '管理项目和关联资源' },
  lineageView: { title: '测试血缘', description: '从结果追溯完整测试链路' },
  collections: { title: '预制用例集', description: '管理预制测试用例集' },
  search: { title: '全局搜索', description: '跨模块搜索' },
}

interface AppShellProps {
  children: React.ReactNode
}

const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const {
    currentUsername,
    currentUserId,
    currentUserRole,
    handleLogout,
    handleSwitchUser,
    switchableUsers,
  } = useAuth()

  const {
    currentPage,
    navigate,
    visibleNavItems,
    navSections,
  } = useNavigation()

  const pageInfo = PAGE_TITLES[currentPage] || { title: 'TestHub' }

  return (
    <div style={styles.shell}>
      <Sidebar
        currentPage={currentPage}
        onNavigate={navigate}
        visibleItems={visibleNavItems}
        sections={navSections}
      />
      <div style={styles.main}>
        <Topbar
          title={pageInfo.title}
          description={pageInfo.description}
          onLogout={handleLogout}
          currentUser={currentUsername}
          currentUserId={currentUserId}
          currentUserRole={currentUserRole}
          onUserClick={() => navigate('profile')}
          onSwitchUser={handleSwitchUser}
          switchableUsers={switchableUsers}
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
  } as const,
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  } as const,
  workspace: {
    flex: 1,
    overflow: 'auto',
    backgroundColor: 'var(--surface-secondary)',
  } as const,
}

export default AppShell
