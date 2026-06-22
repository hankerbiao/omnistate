import type { TestCaseStep } from './index';

export interface StepAnalysisIssue {
  stepIndex: number;
  severity: 'error' | 'warning' | 'suggestion';
  category: 'completeness' | 'consistency' | 'clarity' | 'best_practice' | 'redundancy';
  message: string;
  suggestion?: string;
  field?: 'name' | 'action' | 'expected';
  proposedValue?: string;
}

export interface StepAnalysisResult {
  score: number;
  totalSteps: number;
  issues: StepAnalysisIssue[];
  summary: string;
}

export interface AnalyzeTestStepsRequest {
  steps: TestCaseStep[];
  title?: string;
  category?: string;
  pre_condition?: string;
  post_condition?: string;
}
