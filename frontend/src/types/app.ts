export type PageType = 'requirements' | 'manualTestCases' | 'testCases' | 'agents' | 'tasks' | 'roles' | 'users' | 'profile' | 'myTasks' | 'permissions' | 'dashboard' | 'catalogLabs' | 'testPlanStudio' | 'lineageView' | 'search' | 'collections'

export interface NavItem {
  key: PageType
  label: string
  icon: string
  permission?: string
}

export interface NavSection {
  label: string
  keys: PageType[]
}