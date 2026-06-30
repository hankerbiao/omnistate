import type { ComponentType } from 'react'
import {
  ListTodo, Search, ClipboardList, Zap, FolderKanban, Layers3,
  Bot, CalendarClock, ShieldCheck, BarChart3, Users, Shield,
  GroupIcon, KeyRound, FlaskConical, Settings, Bug,
} from 'lucide-react'
import type { NavItem, NavSection, PageType } from '../types/app'

// ── 界面定义：每个导航项自带 section 归属 ────────────────────────────

export interface NavItemDef extends Omit<NavItem, 'icon' | 'permission'> {
  section: string
  icon: ComponentType<{ className?: string; size?: number | string }>
  permission?: string
}

const NAV_ITEM_DEFS: NavItemDef[] = [
  { key: 'myTasks',      label: '我的任务',         section: '概览',    icon: ListTodo },
  { key: 'search',       label: '全局搜索',         section: '概览',    icon: Search, permission: 'search:global' },

  { key: 'requirements', label: '测试用例编写需求', section: '测试资产', icon: ClipboardList, permission: 'requirements:read' },
  { key: 'testCases',    label: '用例看板',         section: '测试资产', icon: Zap, permission: 'test_cases:read' },
  { key: 'collections',  label: '预制用例集',       section: '测试资产', icon: FolderKanban, permission: 'collections:read' },
  { key: 'projects',     label: '项目',             section: '测试资产', icon: Layers3, permission: 'projects:read' },

  { key: 'agents',               label: '执行代理',   section: '执行', icon: Bot, permission: 'execution_agents:read' },
  { key: 'testPlanStudioDemo',   label: '执行计划',   section: '执行', icon: CalendarClock, permission: 'execution_plans:read' },
  { key: 'caseGovernance',       label: '用例治理',   section: '执行', icon: ShieldCheck, permission: 'case_governance:read' },
  { key: 'failureAnalysis',      label: '失效分析',   section: '执行', icon: Bug, permission: 'execution_tasks:read' },

  { key: 'dashboard',    label: '数据统计',  section: '系统', icon: BarChart3, permission: 'nav:dashboard:view' },
  { key: 'users',        label: '用户管理',  section: '系统', icon: Users, permission: 'users:read' },
  { key: 'roles',        label: '角色管理',  section: '系统', icon: Shield, permission: 'roles:read' },
  { key: 'roleGroup',    label: '用户组管理', section: '系统', icon: GroupIcon, permission: 'roles:read' },
  { key: 'permissions',  label: '权限管理',  section: '系统', icon: KeyRound, permission: 'permissions:read' },
  { key: 'catalogLabs',  label: 'Lab 管理',  section: '系统', icon: FlaskConical, permission: 'catalog:labs:manage' },
  { key: 'systemConfig', label: '系统配置',  section: '系统', icon: Settings, permission: 'system:config' },
]

// ── 对外导出 ─────────────────────────────────────────────────────────

/** NavItem with icon as a component (replaces emoji string) */
export interface NavItemWithIcon extends Omit<NavItem, 'icon'> {
  icon: ComponentType<{ className?: string; size?: number | string }>
}

export const navItemsWithIcons: NavItemWithIcon[] = NAV_ITEM_DEFS.map(({ section: _s, ...rest }) => rest)

/** Legacy: keep original string-icon NavItem for backward compat */
export const navItems: NavItem[] = NAV_ITEM_DEFS.map(({ section: _s, icon: _i, ...rest }) => ({ ...rest, icon: '' }))

export const navSections: NavSection[] = (() => {
  const map = new Map<string, PageType[]>()
  for (const def of NAV_ITEM_DEFS) {
    if (!map.has(def.section)) map.set(def.section, [])
    map.get(def.section)!.push(def.key as PageType)
  }
  return Array.from(map.entries()).map(([label, keys]) => ({ label, keys }))
})()

export function getVisibleNavItemsWithIcons(userPermissions: string[]): NavItemWithIcon[] {
  return navItemsWithIcons.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission)
  })
}

/** Legacy compat */
export function getVisibleNavItems(userPermissions: string[]): NavItem[] {
  return navItems.filter(item => {
    if (!item.permission) return true
    return userPermissions.includes(item.permission)
  })
}

export function resolveDefaultPage(visibleItems: { key: PageType }[]): PageType {
  if (visibleItems.some(item => item.key === 'dashboard')) return 'dashboard'
  if (visibleItems.some(item => item.key === 'myTasks')) return 'myTasks'
  return (visibleItems[0]?.key as PageType) ?? 'profile'
}
