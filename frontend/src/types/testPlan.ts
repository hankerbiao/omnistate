export type PlanComponent =
  | 'BIOS'
  | 'BMC'
  | 'DDR5'
  | 'PCIe'
  | 'Storage'
  | 'Thermal'
  | 'Power'
  | 'Network';

export type PlanPhaseStatus = 'draft' | 'scheduled' | 'triggered' | 'running' | 'done';

export type CaseExecutionMode = 'manual' | 'auto';

export type MilestoneKey = 'kickoff' | 'alpha' | 'beta' | 'rc' | 'ga';

export interface PlanCasePoolItem {
  id: string;
  ref_type: 'manual' | 'auto';
  case_id: string;
  title: string;
  priority: string;
  lab_name: string;
  catalog_path: string[];
  component: PlanComponent;
  default_owner_id: string;
  tags: string[];
}

export interface PlanCaseItem {
  pool_id: string;
  assignee_id: string;
  component: PlanComponent;
  execution_mode: CaseExecutionMode;
}

export interface PlanPhase {
  id: string;
  project_id: string;
  milestone: MilestoneKey;
  name: string;
  component: PlanComponent;
  trigger_at: string;
  lead_id: string;
  status: PlanPhaseStatus;
  cases: PlanCaseItem[];
}

export interface PlanMilestone {
  key: MilestoneKey;
  label: string;
  target_date: string;
  progress: number;
}

export interface TestPlanProject {
  id: string;
  name: string;
  description: string;
  target_date: string;
  status: 'planning' | 'active' | 'completed';
  progress: number;
  milestones: PlanMilestone[];
  phases: PlanPhase[];
}

export const PLAN_COMPONENTS: PlanComponent[] = [
  'BIOS', 'BMC', 'DDR5', 'PCIe', 'Storage', 'Thermal', 'Power', 'Network',
];

export const MILESTONE_LABELS: Record<MilestoneKey, string> = {
  kickoff: '项目启动',
  alpha: '内测阶段',
  beta: '公测阶段',
  rc: '候选发布',
  ga: '正式发布',
};
