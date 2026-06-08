export type PageType = 'requirements' | 'manualTestCases' | 'testCases' | 'agents' | 'tasks' | 'terminal' | 'roles' | 'users' | 'profile' | 'myTasks' | 'permissions' | 'dashboard' | 'catalogLabs' | 'testPlanStudio' | 'lineageView' | 'failureAnalysis' | 'traceability'

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