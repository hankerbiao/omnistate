export type PageType = 'requirements' | 'testCases' | 'agents' | 'tasks' | 'terminal' | 'roles' | 'users'

export interface NavItem {
  key: PageType
  label: string
  icon: string
  permission?: string
}