export type PageType = 'requirements' | 'manualTestCases' | 'testCases' | 'duts' | 'agents' | 'tasks' | 'terminal' | 'roles' | 'users' | 'profile'

export interface NavItem {
  key: PageType
  label: string
  icon: string
  permission?: string
}