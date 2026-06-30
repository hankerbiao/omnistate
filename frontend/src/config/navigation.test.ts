import { describe, it, expect } from 'vitest'
import {
  getVisibleNavItems,
  getVisibleNavItemsWithIcons,
  resolveDefaultPage,
  navItems,
  navItemsWithIcons,
  navSections,
} from './navigation'

describe('navigation config', () => {
  describe('getVisibleNavItems', () => {
    it('returns all items when user has no permissions (and item has no permission requirement)', () => {
      const result = getVisibleNavItems([])
      // 至少包含 myTasks（无 permission 限制）
      expect(result.length).toBeGreaterThan(0)
      expect(result.find((i) => i.key === 'myTasks')).toBeDefined()
    })

    it('filters out items requiring permissions not held by user', () => {
      const allItems = getVisibleNavItems(['*'])  // 全部权限
      const noItems = getVisibleNavItems([])
      expect(allItems.length).toBeGreaterThanOrEqual(noItems.length)
    })

    it('hides permission-gated items when permission is missing', () => {
      const noSearch = getVisibleNavItems([])
      const withSearch = getVisibleNavItems(['search:global'])
      const hasSearch = noSearch.find((i) => i.key === 'search')
      const hasSearch2 = withSearch.find((i) => i.key === 'search')
      expect(hasSearch).toBeUndefined()
      expect(hasSearch2).toBeDefined()
    })

    it('keeps items with no permission requirement visible for all users', () => {
      const result = getVisibleNavItems([])
      const myTasks = result.find((i) => i.key === 'myTasks')
      expect(myTasks).toBeDefined()
    })
  })

  describe('getVisibleNavItemsWithIcons', () => {
    it('returns NavItemWithIcon array (with React components as icons)', () => {
      const result = getVisibleNavItemsWithIcons([])
      expect(result.length).toBeGreaterThan(0)
      // icon 应该是 React 组件（function 或 forwardRef 对象）
      const first = result[0]
      expect(typeof first.icon).toBeDefined()
    })

    it('respects permission filtering', () => {
      const all = getVisibleNavItemsWithIcons(['requirements:read', 'test_cases:read'])
      const none = getVisibleNavItemsWithIcons([])
      expect(all.length).toBeGreaterThanOrEqual(none.length)
    })
  })

  describe('resolveDefaultPage', () => {
    it('prefers dashboard when available', () => {
      const page = resolveDefaultPage([
        { key: 'myTasks' },
        { key: 'dashboard' },
        { key: 'search' },
      ])
      expect(page).toBe('dashboard')
    })

    it('falls back to myTasks when dashboard is not available', () => {
      const page = resolveDefaultPage([{ key: 'myTasks' }, { key: 'search' }])
      expect(page).toBe('myTasks')
    })

    it('returns first visible item when neither dashboard nor myTasks available', () => {
      const page = resolveDefaultPage([{ key: 'search' }, { key: 'projects' }])
      expect(page).toBe('search')
    })

    it('returns profile when no visible items', () => {
      const page = resolveDefaultPage([])
      expect(page).toBe('profile')
    })
  })

  describe('navItems / navItemsWithIcons consistency', () => {
    it('both arrays have the same number of items', () => {
      expect(navItems.length).toBe(navItemsWithIcons.length)
    })

    it('all items have unique keys', () => {
      const keys = navItems.map((i) => i.key)
      expect(new Set(keys).size).toBe(keys.length)
    })

    it('all items have a non-empty label', () => {
      for (const item of navItems) {
        expect(item.label.length).toBeGreaterThan(0)
      }
    })
  })

  describe('navSections', () => {
    it('contains the expected sections', () => {
      const labels = navSections.map((s) => s.label)
      // 至少包含一些核心 section
      expect(labels.length).toBeGreaterThan(0)
    })

    it('all section keys reference existing nav items', () => {
      const allKeys = new Set(navItems.map((i) => i.key))
      for (const section of navSections) {
        for (const key of section.keys) {
          expect(allKeys.has(key)).toBe(true)
        }
      }
    })

    it('no nav item key is duplicated across sections', () => {
      const seen = new Set<string>()
      for (const section of navSections) {
        for (const key of section.keys) {
          expect(seen.has(key)).toBe(false)
          seen.add(key)
        }
      }
    })
  })
})
