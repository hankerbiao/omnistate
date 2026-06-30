import type { TestCaseStep } from './index';

// ═══════════════════════════════════════════════════════════════════════
//  Step Analysis (existing)
// ═══════════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════════
//  Generate Cases (POST /ai/generate-cases)
// ═══════════════════════════════════════════════════════════════════════

export interface GeneratedCaseStep {
  step_id: string;
  name: string;
  action: string;
  expected: string;
}

export interface GeneratedCaseDraft {
  title: string;
  priority: string;
  test_category: string;
  pre_condition: string;
  post_condition: string;
  steps: GeneratedCaseStep[];
  tags: string[];
  rationale: string;
}

export interface GenerateCasesRequest {
  requirement_id?: string;
  requirement_text?: string;
  max_cases?: number;
}

export interface GenerateCasesResponse {
  cases: GeneratedCaseDraft[];
  reason: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  Review Case (POST /ai/review-case)
// ═══════════════════════════════════════════════════════════════════════

export interface ReviewDimension {
  score: number;
  issues: string[];
}

export interface ReviewCaseResponse {
  score: number;
  verdict: 'pass' | 'needs_revision' | 'reject';
  dimensions: Record<string, ReviewDimension>;
  missing_scenarios: string[];
  priority_suggestion: string;
  summary: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  Recommend Cases (POST /ai/recommend-cases)
// ═══════════════════════════════════════════════════════════════════════

export interface RecommendedCase {
  case_id: string;
  reason: string;
  priority_order: number;
}

export interface ExcludedCase {
  case_id: string;
  reason: string;
}

export interface RecommendCasesRequest {
  project_id?: string;
  change_description: string;
  case_ids?: string[];
  max_recommend?: number;
}

export interface RecommendCasesResponse {
  recommended: RecommendedCase[];
  excluded: ExcludedCase[];
  coverage_note: string;
  estimated_runtime_min: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  Failure Analysis (POST /failure-analysis/analyze)
// ═══════════════════════════════════════════════════════════════════════

export interface AnalyzeFailureRequest {
  task_id: string;
  case_id: string;
  execution_log?: string;
  failure_info?: string;
  env_info?: string;
}

export interface AnalyzeFailureResponse {
  root_cause_category: string;
  confidence: number;
  analysis: string;
  probable_cause: string;
  fix_suggestions: string[];
  related_patterns: string[];
  severity: string;
}
