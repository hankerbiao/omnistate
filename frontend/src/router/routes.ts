import type { PageType } from '../types/app'

/**
 * Route path mapping: PageType -> URL path
 * Single source of truth for URL <-> page mapping.
 */
export const PAGE_ROUTES: Record<PageType, string> = {
  myTasks:              '/my-tasks',
  search:               '/search',
  requirements:         '/requirements',
  testCases:            '/test-cases',
  collections:          '/collections',
  projects:             '/projects',
  agents:               '/agents',
  testPlanStudioDemo:   '/execution-plans',
  caseGovernance:       '/case-governance',
  dashboard:            '/dashboard',
  users:                '/users',
  roles:                '/roles',
  roleGroup:            '/role-groups',
  permissions:          '/permissions',
  catalogLabs:          '/catalog-labs',
  systemConfig:         '/system-config',
  profile:              '/profile',
  lineageView:          '/lineage',
  manualTestCases:      '/manual-test-cases',
}

/** Reverse lookup: URL path -> PageType */
export const ROUTE_TO_PAGE: Record<string, PageType> = Object.fromEntries(
  Object.entries(PAGE_ROUTES).map(([page, path]) => [path, page as PageType])
)
