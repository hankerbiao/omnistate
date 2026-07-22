import { describe, expect, it } from 'vitest';
import type { PageType } from '../types/app';
import { getPageHelpDoc, getSectionHelpDocForPage, pageHelpDocs, targetHelpPages } from './pageHelpDocs';

const validPages: PageType[] = [
  'requirements',
  'manualTestCases',
  'testCases',
  'agents',
  'roles',
  'users',
  'profile',
  'myTasks',
  'dashboard',
  'catalogLabs',
  'testPlanStudioDemo',
  'lineageView',
  'collections',
  'projects',
  'systemConfig',
  'caseGovernance',
];

describe('pageHelpDocs', () => {
  it('uses only valid PageType keys', () => {
    const valid = new Set(validPages);
    for (const key of Object.keys(pageHelpDocs)) {
      expect(valid.has(key as PageType)).toBe(true);
    }
  });

  it('contains docs for all target help pages', () => {
    for (const page of targetHelpPages) {
      const doc = getPageHelpDoc(page);
      expect(doc).toBeDefined();
      expect(doc?.page).toBe(page);
      expect(doc?.summary.length).toBeGreaterThan(0);
    }
  });

  it('resolves section overview docs for asset and execution pages', () => {
    expect(getSectionHelpDocForPage('requirements')?.title).toBe('测试资产');
    expect(getSectionHelpDocForPage('testCases')?.title).toBe('测试资产');
    expect(getSectionHelpDocForPage('collections')?.title).toBe('测试资产');
    expect(getSectionHelpDocForPage('projects')?.title).toBe('测试资产');
    expect(getSectionHelpDocForPage('testPlanStudioDemo')?.title).toBe('执行');
    expect(getSectionHelpDocForPage('caseGovernance')?.title).toBe('执行');
    expect(getSectionHelpDocForPage('myTasks')).toBeUndefined();
  });
});
