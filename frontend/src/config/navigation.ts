import type { NavItem, NavSection, PageType } from '../types/app'

// ── 界面定义：每个导航项自带 section 归属 ────────────────────────────

interface NavItemDef extends Omit<NavItem, 'permission'> {
  section: string
  permission?: string
}

const NAV_ITEM_DEFS: NavItemDef[] = [
  { key: 'myTasks',      label: '我的任务',       section: '概览',  icon: '☰' },
  { key: 'search',       label: '全局搜索',       section: '概览',  icon: '🔍', permission: 'search:global' },

  { key: 'requirements', label: '测试用例编写需求', section: '测试资产', icon: '▣', permission: 'requirements:read' },
  { key: 'testCases',    label: '用例看板',        section: '测试资产', icon: '⚡', permission: 'test_cases:read' },
  { key: 'collections',  label: '预制用例集',      section: '测试资产', icon: '📁', permission: 'collections:read' },
  { key: 'projects',     label: '项目',            section: '测试资产', icon: '▣', permission: 'projects:read' },

  { key: 'agents',               label: '执行代理',   section: '执行', icon: '◉', permission: 'execution_agents:read' },
  { key: 'testPlanStudioDemo',   label: '执行计划',   section: '执行', icon: '▤', permission: 'execution_plans:read' },
  { key: 'caseGovernance',       label: '用例治理',   section: '执行', icon: '⬡', permission: 'case_governance:read' },

  { key: 'dashboard',    label: '数据统计',  section: '系统', icon: '◫', permission: 'nav:dashboard:view' },
  { key: 'users',        label: '用户管理',  section: '系统', icon: '⊕', permission: 'users:read' },
  { key: 'roles',        label: '角色管理',  section: '系统', icon: '⊞', permission: 'roles:read' },
  { key: 'roleGroup',    label: '用户组管理', section: '系统', icon: '⊡', permission: 'roles:read' },
  { key: 'permissions',  label: '权限管理',  section: '系统', icon: '◈', permission: 'permissions:read' },
  { key: 'catalogLabs',  label: 'Lab 管理',  section: '系统', icon: '⊟', permission: 'catalog:labs:manage' },
  { key: 'systemConfig', label: '系统配置',  section: '系统', icon: '⚙', permission: 'system:config' },
]

// ── 对外导出 ─────────────────────────────────────────────────────────

export const navItems: NavItem[] = NAV_ITEM_DEFS.map(({ section: _s, ...rest }) => rest)

export const navSections: NavSection[] = (() => {
  const map = new Map<string, string[]>()
  for (const def of NAV_ITEM_DEFS) {
    if (!map.has(def.section)) map.set(def.section, [])
    map.get(def.section)!.push(def.key as string)
  }
  return Array.from(map.entries()).map(([label, keys]) => ({ label, keys }))
})()

export function getVisibleNavItems(userPermissions: string[]): NavItem[] {
  return navItems.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission)
  })
}

export function resolveDefaultPage(visibleItems: NavItem[]): PageType {
  if (visibleItems.some(item => item.key === 'dashboard')) return 'dashboard'
  if (visibleItems.some(item => item.key === 'myTasks')) return 'myTasks'
  return (visibleItems[0]?.key as PageType) ?? 'profile'
}
