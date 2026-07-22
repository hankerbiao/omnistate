/** React Query query key factory — 集中管理所有 query key */
export const queryKeys = {
  permissions: {
    all: ['permissions'] as const,
  },
  roles: {
    all: ['roles'] as const,
  },
  users: {
    all: ['users'] as const,
  },
  requirements: {
    all: ['requirements'] as const,
    filtered: (status?: string) => ['requirements', 'filtered', status] as const,
  },
  testCases: {
    all: ['testCases'] as const,
  },
  workItems: {
    my: (userId: string) => ['workItems', 'my', userId] as const,
  },
  planItems: {
    my: (userId: string) => ['planItems', 'my', userId] as const,
  },
  catalogLabs: {
    all: ['catalogLabs'] as const,
  },
  collections: {
    all: ['collections'] as const,
  },
  dashboard: {
    all: ['dashboard'] as const,
  },
}
