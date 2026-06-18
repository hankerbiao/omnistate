/**
 * 执行计划模块类型定义
 */

export interface PlanSummary {
  plan_id: string;
  title: string;
  description: string;
  status: string;
  start_date: string;
  end_date: string;
  trigger_at: string;
  created_by: string;
  item_count: number;
  done_count: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

export interface PlanItemSummary {
  item_id: string;
  case_id: string;
  case_title: string;
  ref_type: string;
  component: string;
  priority: string;
  assignee_id: string | null;
  status: string;
  order_no: number;
  execution_task_id?: string | null;
  result?: { passed?: boolean; notes?: string; actual?: string } | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type ViewMode = 'statusBoard' | 'componentView' | 'listView';

export const STATUS = ['pending', 'running', 'fail', 'done'] as const;
export type ItemStatus = (typeof STATUS)[number];

export interface PlanDetailViewProps {
  plan: PlanSummary | undefined;
  items: PlanItemSummary[];
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  isEditing: boolean;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onSaveEditing: () => void;
  onRemoveItem: (itemId: string) => void;
  saving: boolean;
  onShowAddCases: () => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
  onRerunItem: (item: PlanItemSummary) => void;
  onBatchAssign: (itemIds: string[], assigneeId: string) => void;
  onTerminateItem: (itemId: string) => void;
  onDeleteItem: (itemId: string) => void;
  onDeletePlan: () => void;
  onUpdateItemAssignee: (itemId: string, assigneeId: string) => void;
}

export interface StatusBoardProps {
  items: PlanItemSummary[];
  isEditing: boolean;
  onRemoveItem: (itemId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
  onRerunItem: (item: PlanItemSummary) => void;
  onTerminateItem: (item: PlanItemSummary) => void;
  onDeleteItem: (item: PlanItemSummary) => void;
  onUpdateItemAssignee: (itemId: string, assigneeId: string) => void;
}

export interface StatusCardProps {
  item: PlanItemSummary;
  isEditing: boolean;
  onRemoveItem: (itemId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
  onRerunItem: (item: PlanItemSummary) => void;
  onTerminateItem: (item: PlanItemSummary) => void;
  onDeleteItem: (item: PlanItemSummary) => void;
  onUpdateItemAssignee: (itemId: string, assigneeId: string) => void;
}

export interface ComponentBoardProps {
  items: PlanItemSummary[];
  isEditing: boolean;
  onRemoveItem: (itemId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
}

export interface DataTableProps {
  items: PlanItemSummary[];
  isEditing: boolean;
  onRemoveItem: (itemId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
  onRerunItem: (item: PlanItemSummary) => void;
  onBatchAssign: (itemIds: string[], assigneeId: string) => void;
  onTerminateItem: (itemId: string) => void;
  onDeleteItem: (itemId: string) => void;
  onUpdateItemAssignee: (itemId: string, assigneeId: string) => void;
}

export interface AddCasesModalProps {
  editingItems: PlanItemSummary[];
  selectedAddCaseIds: string[];
  onToggle: (caseId: string) => void;
  onClose: () => void;
  onConfirm: () => void;
  cases: Record<string, { case_id: string; title: string; type: string; priority: string; created_at: string }>;
  users: { user_id: string; username: string }[];
}

export interface CreatePlanWizardProps {
  wizardStep: number;
  onStepChange: (step: number) => void;
  newPlan: {
    title: string;
    description: string;
    startDate: string;
    endDate: string;
    triggerAt: string;
    selectedCases: string[];
    assignments: Record<string, { assignee: string }>;
  };
  onNewPlanChange: (updates: Partial<CreatePlanWizardProps['newPlan']>) => void;
  caseSearch: string;
  onCaseSearchChange: (search: string) => void;
  submittingPlan: boolean;
  onCreatePlan: () => void;
  onClose: () => void;
  onToggleCase: (caseId: string) => void;
  onToggleCollection: (col: { collection_id: string; name: string }) => void;
  onSetAssignment: (caseId: string, assigneeId: string) => void;
  users: { user_id: string; username: string }[];
  collections: { collection_id: string; name: string; description?: string | null; case_count: number }[];
  caseMap: Map<string, { id: string; title: string; type: 'auto' | 'manual'; priority: string }>;
  casesLoading: boolean;
  currentUserId: string;
}

export interface ArchivedModalProps {
  open: boolean;
  loading: boolean;
  items: (PlanItemSummary & { plan_title?: string })[];
  onClose: () => void;
  onUnarchive: (itemId: string) => void;
  onRerunItem: (item: PlanItemSummary) => void;
}

export interface OverviewViewProps {
  data: Record<string, unknown> | null;
  loading: boolean;
  onRefresh: () => void;
  onSelectPlan: (planId: string) => void;
  users: { user_id: string; username: string }[];
  onViewResult: (item: PlanItemSummary, taskData: unknown, timelineData: unknown) => void;
  onTerminateItem: (item: PlanItemSummary) => void;
  onDeleteItem: (item: PlanItemSummary) => void;
  onCancelExecution: (itemId: string) => void;
}

export interface ResultModalProps {
  item: PlanItemSummary;
  taskData: unknown;
  timelineData: unknown;
  loading: boolean;
  error?: string;
  onClose: () => void;
}

export interface RerunConfirmModalProps {
  item: PlanItemSummary;
  users: { user_id: string; username: string }[];
  onConfirm: (assigneeId: string) => void;
  onClose: () => void;
}