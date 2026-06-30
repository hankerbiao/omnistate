import type { ComponentType } from 'react'

export type PageType = 'requirements' | 'manualTestCases' | 'testCases' | 'agents' | 'roles' | 'roleGroup' | 'users' | 'profile' | 'myTasks' | 'permissions' | 'dashboard' | 'catalogLabs' | 'testPlanStudioDemo' | 'lineageView' | 'search' | 'collections' | 'projects' | 'systemConfig' | 'caseGovernance' | 'failureAnalysis'

export interface NavItem {
  key: PageType
  label: string
  icon: string
  permission?: string
}

/** New: NavItem with Lucide icon component instead of emoji string */
export interface NavItemWithIcon {
  key: PageType
  label: string
  icon: ComponentType<{ className?: string; size?: number | string }>
  permission?: string
}

export interface NavSection {
  label: string
  keys: PageType[]
}
