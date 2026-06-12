import type { NavItem, NavSection, PageType } from '../types/app'

export const navItems: NavItem[] = [
  { key: 'dashboard', label: '数据统计', icon: '◫', permission: 'nav:dashboard:view' },
  { key: 'myTasks', label: '我的任务', icon: '☰' },
  { key: 'search', label: '全局搜索', icon: '🔍' },
  { key: 'requirements', label: '测试用例编写需求', icon: '▣' },
  { key: 'testCases', label: '用例看板', icon: '⚡' },
  { key: 'collections', label: '预制用例集', icon: '📁' },
  { key: 'agents', label: '执行代理', icon: '◉' },
  { key: 'testPlanStudioDemo', label: '执行计划', icon: '▤' },
  { key: 'caseGovernance', label: '用例治理', icon: '⬡' },
  { key: 'users', label: '用户管理', icon: '⊕', permission: 'users:read' },
  { key: 'roles', label: '角色管理', icon: '⊞', permission: 'roles:read' },
  { key: 'roleGroup', label: '用户组管理', icon: '⊡', permission: 'roles:read' },
  { key: 'permissions', label: '权限管理', icon: '◈', permission: 'permissions:read' },
  { key: 'catalogLabs', label: 'Lab 管理', icon: '⊟', permission: 'catalog:labs:manage' },
  { key: 'systemConfig', label: '系统配置', icon: '⚙', permission: 'system:config' },
]

export const navSections: NavSection[] = [
  { label: '概览', keys: ['myTasks', 'search'] },
  { label: '测试资产', keys: ['requirements', 'testCases', 'collections'] },
  { label: '执行', keys: ['agents', 'testPlanStudioDemo', 'caseGovernance'] },
  { label: '系统', keys: ['dashboard', 'users', 'roles', 'roleGroup', 'permissions', 'catalogLabs', 'systemConfig'] },
]

export function getVisibleNavItems(userPermissions: string[]): NavItem[] {
  return navItems.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission) || userPermissions.some(p => p.startsWith('roles:'))
  })
}

export function resolveDefaultPage(visibleItems: NavItem[]): PageType {
  if (visibleItems.some(item => item.key === 'dashboard')) return 'dashboard'
  if (visibleItems.some(item => item.key === 'myTasks')) return 'myTasks'
  return visibleItems[0]?.key ?? 'profile'
}
