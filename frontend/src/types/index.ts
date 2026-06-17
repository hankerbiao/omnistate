// ═══════════════════════════════════════════════════════════════════════
//  通用基类（Shared Base Interfaces）
// ═══════════════════════════════════════════════════════════════════════

/** 基础用例字段，用于 Create/Response 类型继承 */
export interface BaseTestCaseFields {
  title: string;
  priority?: string;
  tags?: string[];
  test_category?: string;
  is_destructive?: boolean;
  pre_condition?: string;
  post_condition?: string;
  is_need_auto?: boolean;
  is_automated?: boolean;
  automation_type?: string;
  script_entity_id?: string;
  automation_case_ref?: AutomationCaseRef;
  risk_level?: string;
  failure_analysis?: string;
  confidentiality?: string;
  visibility_scope?: string;
  attachments?: Record<string, unknown>[];
  custom_fields?: Record<string, unknown>;
  deprecation_reason?: string;
  approval_history?: Record<string, unknown>[];
  steps?: TestCaseStep[];
  cleanup_steps?: TestCaseStep[];
}

/** 通用分页查询参数 */
export interface PaginationParams {
  limit?: number;
  offset?: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  API 通用（General Api）
// ═══════════════════════════════════════════════════════════════════════

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// ═══════════════════════════════════════════════════════════════════════
//  用户/认证相关（Auth & User）
// ═══════════════════════════════════════════════════════════════════════

export interface LoginRequest {
  user_id: string;
  password: string;
}

export interface LoginResponse {
  code: number;
  message: string;
  data: {
    access_token: string;
    token_type: string;
    user: {
      id: string;
      user_id: string;
      username: string;
      email?: string;
      role_ids: string[];
      status: string;
    };
  };
}

export interface User {
  id: string;
  username: string;
  email?: string;
}

export interface UserResponse {
  id: string;
  user_id: string;
  username: string;
  email?: string;
  role_ids: string[];
  extra_permission_ids?: string[];
  allowed_nav_views?: string[];
  status: string;
  itcode?: string;
  subscribe_notifications?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  user_id: string;
  username: string;
  password: string;
  email?: string;
  role_ids?: string[];
  status?: string;
  itcode?: string;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
  status?: string;
  itcode?: string;
  subscribe_notifications?: boolean;
}

export interface UpdateUserRolesRequest {
  role_ids: string[];
}

export interface UpdateUserExtraPermissionsRequest {
  extra_permission_ids: string[];
}

export interface UserEffectivePermissionsResponse {
  user_id: string;
  role_ids: string[];
  extra_permission_ids: string[];
  role_permissions: string[];
  extra_permissions: string[];
  permissions: string[];
}

export interface UpdateUserPasswordRequest {
  new_password: string;
}

export interface ListUsersParams extends PaginationParams {
  status?: string;
  role_id?: string;
  search?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  权限/角色相关（Role & Permission）
// ═══════════════════════════════════════════════════════════════════════

export interface PermissionResponse {
  id: string;
  /** 业务权限 ID，与角色 permission_ids 一致 */
  perm_id: string;
  /** @deprecated 使用 perm_id */
  permission_id?: string;
  name: string;
  code: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface RoleResponse {
  id: string;
  role_id: string;
  name: string;
  description?: string;
  permission_ids?: string[];
  is_system?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
  permission_ids?: string[];
}

export interface UpdateRoleRequest {
  name?: string;
  description?: string;
}

export interface UpdateRolePermissionsRequest {
  permission_ids: string[];
}

export interface CurrentUserPermissionsResponse {
  user_id: string;
  permissions: string[];
  roles: {
    role_id: string;
    role_name: string;
  }[];
}

// ═══════════════════════════════════════════════════════════════════════
//  导航相关（Navigation）
// ═══════════════════════════════════════════════════════════════════════

export interface NavigationPageResponse {
  id?: string;
  view: string;
  label: string;
  permission?: string | null;
  description?: string | null;
  order: number;
  is_active: boolean;
}

export interface UserNavigationResponse {
  user_id: string;
  role_ids: string[];
  permissions: string[];
  allowed_nav_views: string[];
  role_derived_nav_views: string[];
  has_nav_override: boolean;
}

export interface UpdateUserNavigationRequest {
  allowed_nav_views: string[];
}

// ═══════════════════════════════════════════════════════════════════════
//  工作流相关（Workflow）
// ═══════════════════════════════════════════════════════════════════════

export interface WorkItem {
  item_id: string;
  type_code: string;
  title: string;
  content: string;
  parent_item_id?: string;
  current_state: string;
  current_owner_id?: string;
  creator_id: string;
  created_at: string;
  updated_at: string;
  req_id?: string;
  case_id?: string;
}

export interface WorkflowTransition {
  action: string;
  to_state: string;
  target_owner_strategy: string;
  required_fields: string[];
}

export interface WorkflowTransitionsResponse {
  item_id: string;
  current_state: string;
  available_transitions: WorkflowTransition[];
  creator?: string;
  current_owner?: string;
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowTransitionRequest {
  action: string;
  form_data?: Record<string, unknown>;
}

export interface WorkflowTransitionResponse {
  work_item_id: string;
  from_state: string;
  to_state: string;
  action: string;
  new_owner_id?: string;
}

export interface WorkflowTransitionLog {
  id: string;
  work_item_id: string;
  from_state: string;
  to_state: string;
  action: string;
  operator_id: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  TestCase 相关
// ═══════════════════════════════════════════════════════════════════════

export interface TestCaseStep {
  step_id: string;
  name: string;
  action: string;
  expected: string;
}

export interface AutomationCaseRef {
  auto_case_id: string;
  version?: string;
}

export interface CreateTestCaseRequest extends BaseTestCaseFields {
  case_id?: string;
  ref_req_id?: string;
  lab_id: string;
  catalog_path: string[];
  version?: number;
  is_active?: boolean;
  change_log?: string;
  owner_id?: string;
  reviewer_id?: string;
  auto_dev_id?: string;
  estimated_duration_sec?: number;
  required_env?: Record<string, unknown>;
}

export type UpdateTestCaseRequest = Partial<Omit<CreateTestCaseRequest, 'case_id'>>;

export interface TestCaseResponse extends BaseTestCaseFields {
  id: string;
  case_id: string;
  ref_req_id?: string | null;
  lab_id: string;
  lab_name?: string | null;
  catalog_path: string[];
  catalog_path_key?: string;
  catalog_breadcrumb?: string | null;
  version: number;
  is_active: boolean;
  change_log?: string;
  status: string;
  workflow_item_id?: string;
  owner_id?: string;
  reviewer_id?: string;
  auto_dev_id?: string;
  estimated_duration_sec?: number;
  required_env: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TestCaseFieldChange {
  field: string;
  old_value: unknown;
  new_value: unknown;
  change_type: 'added' | 'removed' | 'modified';
}

export interface TestCaseChangeLog {
  id: string;
  case_id: string;
  revision_no: number;
  action: string;
  operator_id: string;
  operator_name?: string | null;
  changes: TestCaseFieldChange[];
  remark?: string | null;
  created_at: string;
}

export interface TestCaseChangeLogListResponse {
  items: TestCaseChangeLog[];
  total: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  测试用例执行统计
// ═══════════════════════════════════════════════════════════════════════

export interface ExecutionRecord {
  result_id: string;
  passed: boolean;
  executed_by: string;
  executed_at: string;
  plan_id: string;
  notes: string;
}

export interface ExecutionStatsResponse {
  case_id: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  last_executed_at: string | null;
  recent: ExecutionRecord[];
}

export interface ListTestCasesParams extends PaginationParams {
  ref_req_id?: string;
  status?: string;
  owner_id?: string;
  reviewer_id?: string;
  priority?: string;
  is_active?: boolean;
  lab_id?: string;
  catalog_prefix?: string;
  tags?: string;
  missing_fields?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  TestCase 评论（Comment）
// ═══════════════════════════════════════════════════════════════════════

export interface TestCaseComment {
  _id: string;
  comment_id: string;
  case_id: string;
  content: string;
  author_id: string;
  author_name?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface CommentListResponse {
  items: TestCaseComment[];
  total: number;
}

export interface CreateCommentRequest {
  content: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  Requirement 相关
// ═══════════════════════════════════════════════════════════════════════

export interface RequirementKeyParameter {
  name: string;
  value: string;
}

export interface CreateRequirementRequest {
  title: string;
  description?: string;
  category?: string;
  tags?: string[];
  source?: string;
  acceptance_criteria?: string;
  baseline_version?: string;
  target_version?: string;
  target_components?: string[];
  firmware_version?: string;
  priority?: string;
  key_parameters?: RequirementKeyParameter[];
  risk_points?: string;
  tpm_owner_id?: string;
  manual_dev_id?: string;
  auto_dev_id?: string;
  attachments?: Record<string, unknown>[];
  planned_start_date?: string;
  planned_end_date?: string;
}

export interface RequirementResponse {
  id: string;
  req_id: string;
  workflow_item_id?: string;
  title: string;
  description?: string;
  category?: string;
  tags: string[];
  source?: string;
  acceptance_criteria?: string;
  baseline_version?: string;
  target_version?: string;
  target_components: string[];
  firmware_version?: string;
  priority: string;
  key_parameters: RequirementKeyParameter[];
  risk_points?: string;
  tpm_owner_id: string;
  tpm_owner_name?: string;
  manual_dev_id?: string;
  manual_dev_name?: string;
  auto_dev_id?: string;
  auto_dev_name?: string;
  case_count: number;
  status: string;
  attachments: Record<string, unknown>[];
  planned_start_date?: string;
  planned_end_date?: string;
  created_at: string;
  updated_at: string;
  // Workflow related fields
  creator?: string;
  creator_name?: string;
  current_owner?: string;
  current_owner_name?: string;
}

export interface ListRequirementsParams extends PaginationParams {
  status?: string;
  category?: string;
  source?: string;
  tpm_owner_id?: string;
  manual_dev_id?: string;
  auto_dev_id?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  Catalog / Lab 相关
// ═══════════════════════════════════════════════════════════════════════

export interface CatalogLab {
  lab_id: string;
  code: string;
  name: string;
  description?: string | null;
  sort_order: number;
  is_active: boolean;
  case_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCatalogLabRequest {
  code: string;
  name: string;
  description?: string;
  sort_order?: number;
}

export interface UpdateCatalogLabRequest {
  name?: string;
  description?: string;
  sort_order?: number;
}

export interface CatalogTreeNode {
  name: string;
  path: string[];
  case_count: number;
  children: CatalogTreeNode[];
}

export interface CatalogTreeResponse {
  lab_id: string;
  tree: CatalogTreeNode;
}

// ═══════════════════════════════════════════════════════════════════════
//  下发（Dispatch）相关
// ═══════════════════════════════════════════════════════════════════════

export interface DispatchCaseItem {
  auto_case_id: string;
  config?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
}

export interface AttachmentInfo {
  file_id: string;
  original_filename: string;
  storage_path: string;
  size: number;
  content_type: string;
  sha256?: string | null;
  uploaded_by?: string;
  uploaded_at: string;
  download_url?: string | null;
}

export interface AutomationConfigFieldOption {
  label?: string;
  value: string | number | boolean;
}

export interface AutomationConfigField {
  type_marker?: string;
  __type__?: string;
  name: string;
  label?: string;
  type?: string;
  default?: unknown;
  required?: boolean;
  options?: AutomationConfigFieldOption[] | null;
  extensions?: Record<string, unknown> | null;
  description?: string;
  extra_props?: Record<string, unknown>;
}

export interface DispatchTaskRequest {
  schedule_type?: string;
  planned_at?: string;
  callback_url?: string;
  category?: string;
  project_tag?: string;
  repo_url?: string;
  branch?: string;
  pytest_options?: Record<string, unknown>;
  timeout?: number;
  dut?: Record<string, unknown>;
  cases: DispatchCaseItem[];
  attachments?: AttachmentInfo[];
  execution_config?: ExecutionConfig;
}

export interface RerunTaskRequest {
  schedule_type?: string;
  planned_at?: string;
  callback_url?: string;
  category?: string;
  project_tag?: string;
  repo_url?: string;
  branch?: string;
  pytest_options?: Record<string, unknown>;
  timeout?: number;
  dut?: Record<string, unknown>;
  cases?: DispatchCaseItem[];
  attachments?: AttachmentInfo[];
  execution_config?: ExecutionConfig;
}

export interface DispatchTaskResponse {
  task_id: string;
  source_task_id?: string;
  dispatch_status: string;
  overall_status: string;
  case_count: number;
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  自动化用例（Automation TestCase）相关
// ═══════════════════════════════════════════════════════════════════════

export interface CreateAutomationTestCaseRequest {
  auto_case_id?: string;
  name: string;
  version?: string;
  status?: string;
  framework?: string;
  automation_type?: string;
  repo_url?: string;
  repo_branch?: string;
  script_path?: string;
  script_entity_id?: string;
  entry_command?: string;
  runtime_env?: Record<string, unknown>;
  tags?: string[];
  maintainer_id?: string;
  reviewer_id?: string;
  description?: string;
}

export interface AutomationTestCaseResponse {
  id: string;
  auto_case_id: string;
  linked_manual_case_id?: string;
  name: string;
  version: string;
  status: string;
  framework?: string;
  automation_type?: string;
  repo_url?: string;
  repo_branch?: string;
  script_path?: string;
  script_name?: string;
  script_entity_id?: string;
  entry_command?: string;
  runtime_env: Record<string, unknown>;
  tags: string[];
  maintainer_id?: string;
  reviewer_id?: string;
  description?: string;
  param_spec?: AutomationConfigField[];
  report_meta?: {
    timeout?: number;
  };
  code_snapshot?: {
    branch?: string;
    commit_id?: string;
    commit_short_id?: string;
    author?: string;
    commit_time?: string;
    message?: string;
  };
  script_ref?: {
    entity_id?: string;
    module?: string;
    project_tag?: string;
    project_scope?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface ListAutomationTestCasesParams extends PaginationParams {
  framework?: string;
  automation_type?: string;
  status?: string;
  maintainer_id?: string;
  linked_manual_case_id?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  执行代理（Agent）相关
// ═══════════════════════════════════════════════════════════════════════

export interface ExecutionAgent {
  agent_id: string;
  hostname: string;
  ip: string;
  port?: number;
  base_url?: string;
  region: string;
  status: string;
  registered_at: string;
  last_heartbeat_at: string;
  heartbeat_ttl_seconds: number;
  lease_expires_at: string;
  is_online: boolean;
  created_at: string;
  updated_at: string;
}

export interface ListAgentsParams {
  region?: string;
  status?: string;
  online_only?: boolean;
}

export interface AgentCleanupOfflineResponse {
  deleted_count: number;
  deleted_agent_ids: string[];
}

// ═══════════════════════════════════════════════════════════════════════
//  执行任务（Execution Task）相关
// ═══════════════════════════════════════════════════════════════════════

export interface ExecutionTask {
  task_id: string;
  source_task_id?: string;
  agent_id?: string;
  dispatch_channel: string;
  dedup_key?: string;
  schedule_type: string;
  schedule_status: string;
  dispatch_status: string;
  consume_status: string;
  overall_status: string;
  case_count: number;
  auto_case_ids?: string[];
  current_case_id?: string;
  current_auto_case_id?: string;
  current_case_index?: number;
  planned_at?: string;
  triggered_at?: string;
  created_at: string;
  updated_at: string;
  cases?: ExecutionTaskCaseSummary[];
}

export interface TaskStatus {
  task_id: string;
  source_task_id?: string;
  agent_id?: string;
  dispatch_channel: string;
  dedup_key?: string;
  schedule_type: string;
  schedule_status: string;
  dispatch_status: string;
  consume_status: string;
  overall_status: string;
  case_count: number;
  planned_at?: string;
  triggered_at?: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  cases?: ExecutionTaskCaseSummary[];
  result_summary?: Record<string, unknown>;
  request_payload?: {
    // 顶层结构（20260520 新增）
    action?: string;
    data?: {
      task_id?: string;
      category?: string;
      project_tag?: string;
      repo_url?: string;
      branch?: string;
      pytest_options?: Record<string, unknown>;
      timeout?: number;
      cases?: Array<{
        case_id?: string;
        script_path?: string;
        script_name?: string;
        parameters?: Record<string, unknown>;  // file 类型字段值为空字符串
      }>;
      files?: Record<string, {
        url?: string | null;
        sha256?: string | null;
      }>;
    };
    // 兼容旧结构
    schedule_type?: string;
    planned_at?: string;
    callback_url?: string;
    category?: string;
    project_tag?: string;
    repo_url?: string;
    branch?: string;
    pytest_options?: Record<string, unknown>;
    timeout?: number;
    dut?: Record<string, unknown>;
    attachments?: AttachmentInfo[];
    execution_config?: ExecutionConfig;
    cases?: Array<{
      auto_case_id?: string;
      script_entity_id?: string;
      config?: Record<string, unknown>;
      script_path?: string;
      script_name?: string;
      parameters?: Record<string, unknown>;
    }>;
  };
}

export interface ExecutionAssertionItem {
  seq?: number;
  name?: string;
  status?: string;
  data?: Record<string, unknown>;
  error?: Record<string, unknown>;
  timestamp?: string;
}

export interface ExecutionCaseResultData {
  event_type?: string;
  phase?: string;
  status?: string;
  total_cases?: number;
  started_cases?: number;
  finished_cases?: number;
  failed_cases?: number;
  assertions?: ExecutionAssertionItem[];
  data?: Record<string, unknown>;
  error?: Record<string, unknown>;
}

export interface ExecutionTaskCaseSummary {
  task_id: string;
  case_id: string;
  auto_case_id?: string;
  order_no: number;
  title?: string;
  status: string;
  progress_percent?: number;
  dispatch_status: string;
  dispatch_attempts: number;
  event_count: number;
  failure_message?: string;
  started_at?: string;
  finished_at?: string;
  last_event_id?: string;
  last_event_at?: string;
  result_data?: ExecutionCaseResultData;
}

export interface ListTasksParams extends PaginationParams {
  schedule_type?: string;
  schedule_status?: string;
  dispatch_status?: string;
  consume_status?: string;
  overall_status?: string;
  created_by?: string;
  agent_id?: string;
  date_from?: string;
  date_to?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  执行配置（Execution Config）
// ═══════════════════════════════════════════════════════════════════════

export type StepFailurePolicy =
  | 'CONTINUE'           // 继续后续步骤
  | 'STOP_WAIT'          // 停止等待
  | 'STOP_NOTIFY'        // 停止+通知
  | 'STOP_WAIT_MANUAL'   // 停止+等待人工继续
  | 'RETRY_UNTIL_SUCCESS' // 重复运行直到成功
  | 'RETRY_N_TIMES_CONTINUE'; // 重复运行N次后继续

export type CaseFailurePolicy =
  | 'CONTINUE'           // 继续后续case
  | 'STOP'               // 停止
  | 'STOP_NOTIFY'        // 停止+通知
  | 'STOP_WAIT_MANUAL'   // 停止+等待人工继续
  | 'RETRY_UNTIL_SUCCESS' // 重复运行直到成功
  | 'RETRY_N_TIMES_CONTINUE'; // 重复运行N次后继续

export interface ExecutionConfig {
  step_on_failure: StepFailurePolicy;
  step_retry_count?: number;  // 当使用 RETRY_N_TIMES_CONTINUE 时有效
  case_on_failure: CaseFailurePolicy;
  case_retry_count?: number;  // 当使用 RETRY_N_TIMES_CONTINUE 时有效
}

// ═══════════════════════════════════════════════════════════════════════
//  血缘图谱（Lineage Graph）
// ═══════════════════════════════════════════════════════════════════════

export interface LineageNode {
  id: string;
  type: 'requirement' | 'test_case' | 'automation_case' | 'task' | 'case_result' | 'agent';
  label: string;
  status?: string;
  subtitle?: string;
  meta: Record<string, unknown>;
}

export interface LineageEdge {
  source: string;
  target: string;
  label: string;
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root_id: string;
  root_type: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  全局搜索（Global Search）
// ═══════════════════════════════════════════════════════════════════════

export interface SearchItem {
  id: string;
  title: string;
  subtitle?: string | null;
  type: string;
  type_label: string;
  highlight?: string | null;
  url: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SearchGroup {
  type: string;
  type_label: string;
  items: SearchItem[];
  total: number;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchGroup[];
}

// ═══════════════════════════════════════════════════════════════════════
//  预制用例集（TestCaseCollection）
// ═══════════════════════════════════════════════════════════════════════

export interface CollectionListItem {
  collection_id: string;
  name: string;
  description?: string | null;
  tags: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  updated_at: string;
}

export interface CollectionResponse {
  collection_id: string;
  name: string;
  description?: string | null;
  tags: string[];
  case_ids: string[];
  auto_case_ids: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string;
  tags?: string[];
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface UpdateCollectionRequest {
  name?: string;
  description?: string;
  tags?: string[];
}

export interface AddCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface RemoveCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}

// ═══════════════════════════════════════════════════════════════════════
//  执行计划（ExecutionPlan / My Tasks）
// ═══════════════════════════════════════════════════════════════════════

export interface PlanTaskResultPayload {
  passed: boolean;
  notes: string;
  severity: string;
  actual: string;
  expected: string;
  env: string;
  test_data: string;
  bug_id: string;
  actual_duration: string;
  attachments: string[];
  executed_at?: string;
}

export interface PlanTaskItemResponse {
  item_id: string;
  plan_id: string;
  plan_title: string;
  case_id: string;
  case_title: string;
  ref_type: string;       // 'manual' | 'auto'
  component: string;
  priority: string;
  assignee_id: string | null;
  status: string;          // 'pending' | 'running' | 'done' | 'fail'
  order_no: number;
  execution_task_id: string | null;
  result: PlanTaskResultPayload | null;
}

export interface SubmitManualResultRequest {
  passed: boolean;
  notes?: string;
  severity?: string;
  actual?: string;
  expected?: string;
  env?: string;
  test_data?: string;
  bug_id?: string;
  actual_duration?: string;
  attachments?: string[];
  executed_at?: string;
}

export interface PlanItemDispatchRequest {
  agent_id?: string;
  schedule_type?: string;
  planned_at?: string;
  category?: string;
  project_tag?: string;
  repo_url?: string;
  branch?: string;
  pytest_options?: Record<string, unknown>;
  timeout?: number;
  parameters?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface PlanItemRerunRequest {
  assignee_id?: string;
}

export interface PlanItemDispatchConfig {
  schedule_type: string;
  planned_at?: string;
  parameters?: Record<string, unknown>;
}

export interface BatchDispatchPlanItemsRequest {
  item_ids: string[];
  agent_id?: string;
  schedule_type?: string;
  planned_at?: string;
  category?: string;
  project_tag?: string;
  pytest_options?: Record<string, unknown>;
  timeout?: number;
  parameters?: Record<string, unknown>;
}

export interface CreatePlanRequest {
  title: string;
  description?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  trigger_at?: string;
}

export interface PlanItemInput {
  ref_type: string;    // 'manual' | 'auto'
  case_id: string;
  assignee_id?: string;
  component?: string;
  order_no?: number;
}

export interface AddPlanItemsRequest {
  items: PlanItemInput[];
}

export interface BatchUpdateAssigneeRequest {
  item_ids: string[];
  assignee_id?: string;
}

// ═══════════════════════════════════════════════════════════════════════
//  系统配置（System Config）
// ═══════════════════════════════════════════════════════════════════════

export interface SystemConfig {
  id: number;
  config_key: string;
  config_value: string;
  config_type: 'string' | 'integer' | 'float' | 'boolean' | 'json';
  category: 'ai' | 'system' | 'general';
  description: string;
  is_encrypted: boolean;
  is_active: boolean;
  needs_restart: boolean;
  created_at: string;
  updated_at: string;
  updated_by?: string;
}

export interface TestConnectionRequest {
  base_url: string;
  model: string;
  api_key?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  model?: string;
  response_time_ms?: number;
  error?: string;
}

export interface BatchUpdateConfigRequest {
  items: Array<{
    config_key: string;
    config_value: string;
  }>;
  remark?: string;
}

export interface ConfigHistory {
  id: number;
  config_key: string;
  old_value: string;
  new_value: string;
  changed_by: string;
  changed_at: string;
  remark?: string;
}

export interface SystemConfigListResponse {
  items: SystemConfig[];
  total: number;
}

// ═══════════════════════════════════════════════════════════════════════
//  AI 分析相关（AIAnalysis）
// ═══════════════════════════════════════════════════════════════════════

export interface AnalysisIssue {
  case_id: string;
  field: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
}

export interface DuplicatePair {
  case_id1: string;
  case_id2: string;
  similarity: number;
  reason: string;
}

export interface QualityAnalysis {
  score: number;
  issues: AnalysisIssue[];
}

export interface RedundancyAnalysis {
  score: number;
  duplicates: DuplicatePair[];
}

export interface CoverageAnalysis {
  score: number;
  gaps: string[];
}

// ═══════════════════════════════════════════════════════════════════════
//  用例集合（Test Case Collection）
// ═══════════════════════════════════════════════════════════════════════

export interface CollectionListItem {
  collection_id: string;
  name: string;
  description: string | null;
  tags: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  updated_at: string;
}

export interface CollectionResponse {
  collection_id: string;
  name: string;
  description: string | null;
  tags: string[];
  case_ids: string[];
  auto_case_ids: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string | null;
  tags?: string[];
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface UpdateCollectionRequest {
  name?: string | null;
  description?: string | null;
  tags?: string[] | null;
}

export interface AddCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface RemoveCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface CollectionAnalysisResult {
  collection_id: string;
  overall_score: number;
  quality: QualityAnalysis;
  redundancy: RedundancyAnalysis;
  coverage: CoverageAnalysis;
  recommendations: string[];
}

// ═══════════════════════════════════════════════════════════════════════
//  用例治理（Case Governance）
// ═══════════════════════════════════════════════════════════════════════

export interface GovernanceStats {
  total_manual: number;
  total_auto: number;
  missing_lab: number;
  missing_catalog: number;
  missing_tags: number;
  unlinked_auto: number;
}

export interface BatchUpdateCasesRequest {
  case_ids: string[];
  lab_id?: string;
  catalog_path?: string[];
  tags_add?: string[];
  tags_remove?: string[];
}

export interface BatchUpdateResult {
  updated_count: number;
  failed_count: number;
  failures: { case_id: string; reason: string }[];
}

// ═══════════════════════════════════════════════════════════════════════
//  Execution Timeline types
// ═══════════════════════════════════════════════════════════════════════

export interface TaskTimelineEvent {
  event_id: string;
  task_id: string;
  case_id?: string | null;
  event_type: string;
  phase?: string | null;
  event_seq?: number | null;
  event_status?: string | null;
  event_timestamp: string;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  ingested_at: string;
}

export interface TaskBizLog {
  id: string;
  task_id: string;
  case_id?: string | null;
  event_id?: string | null;
  node: string;
  action: string;
  outcome?: string | null;
  status_before?: Record<string, unknown> | null;
  status_after?: Record<string, unknown> | null;
  operator_id?: string | null;
  request_id?: string | null;
  detail: Record<string, unknown>;
  level: string;
  created_at: string;
}

export interface TaskTimeline {
  biz_logs: TaskBizLog[];
  events: TaskTimelineEvent[];
}

// ═══════════════════════════════════════════════════════════════════════
//  系统枚举（System Enums）
// ═══════════════════════════════════════════════════════════════════════

export interface EnumMap {
  workflow_states: string[];
  owner_strategies: string[];
  priority: string[];
  requirement_category: string[];
  requirement_source: string[];
  automation_case_status: string[];
  manual_case_status: string[];
  confidentiality: string[];
  visibility_scope: string[];
  risk_level: string[];
  test_category: string[];
  execution_overall_status: string[];
  execution_case_status: string[];
  execution_dispatch_status: string[];
  execution_schedule_status: string[];
  execution_consume_status: string[];
  execution_agent_status: string[];
  execution_final_statuses: string[];
  plan_item_status: string[];
  plan_status: string[];
  task_to_item_status: Record<string, string>;
  config_types: string[];
  config_categories: string[];
}
