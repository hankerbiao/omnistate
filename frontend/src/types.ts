export enum TestCaseStatus {
  DRAFT = 'draft',
  REVIEW = 'review',
  APPROVED = 'approved',
  DEPRECATED = 'deprecated'
}

export enum Priority {
  P0 = 'P0',
  P1 = 'P1',
  P2 = 'P2'
}

export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high'
}

export enum VisibilityScope {
  TEAM = 'team',
  PROJECT = 'project',
  GLOBAL = 'global'
}

export interface TestStep {
  step_id: string;
  name: string;
  action: string;
  expected: string;
}

export interface ApprovalRecord {
  approver: string;
  timestamp: string;
  result: 'approved' | 'rejected' | 'commented';
  comment: string;
}

export enum TestCaseCategory {
  FUNCTIONAL = 'functional',
  STRESS = 'stress',
  PERFORMANCE = 'performance',
  COMPATIBILITY = 'compatibility',
  STABILITY = 'stability',
  SECURITY = 'security'
}

export enum Confidentiality {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  NDA = 'nda'
}

export enum RequirementStatus {
  PENDING = '待指派',
  DEVELOPING = '用例开发中',
  REVIEWING = '评审中',
  CLOSED = '已闭环'
}

export interface TestRequirement {
  req_id: string;
  title: string;
  description: string;
  technical_spec?: string;
  target_components: string[];
  firmware_version?: string;
  priority: Priority;
  key_parameters: { key: string; value: string }[];
  risk_points?: string;
  tpm_owner_id: string;
  manual_dev_id: string;
  status: RequirementStatus;
  attachments: Attachment[];
  created_at: string;
  updated_at: string;
}

export interface Attachment {
  id: string;
  name: string;
  type: 'image' | 'video' | 'spec' | 'log' | 'other';
  url: string;
  size?: string;
  uploaded_at: string;
}

export interface TestCase {
  case_id: string;
  ref_req_id: string;
  title: string;
  test_category: TestCaseCategory; // New
  version: number;
  is_active: boolean;
  change_log: string;
  status: TestCaseStatus;
  owner_id: string;
  reviewer_id: string;
  auto_dev_id?: string;
  priority: Priority;
  estimated_duration_sec: number;
  target_components: string[];
  required_env: {
    os?: string;
    firmware?: string;
    hardware?: string;
    dependencies?: string[];
    tooling?: string[]; // New
  };
  tags: string[];
  pre_condition: string;
  post_condition: string; // New
  cleanup_steps: TestStep[]; // New
  steps: TestStep[];
  is_need_auto: boolean;
  is_destructive: boolean; // New
  automation_type: string;
  script_entity_id: string;
  risk_level: RiskLevel;
  visibility_scope: VisibilityScope;
  confidentiality: Confidentiality; // New
  attachments: Attachment[];
  custom_fields: Record<string, string>;
  failure_analysis?: string; // New
  deprecation_reason?: string;
  approval_history: ApprovalRecord[];
  created_at: string;
  updated_at: string;
}
