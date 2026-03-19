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

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface User {
  id: string;
  username: string;
  email?: string;
}

export interface RequirementKeyParameter {
  name: string;
  value: string;
}

export interface CreateRequirementRequest {
  title: string;
  description?: string;
  technical_spec?: string;
  target_components?: string[];
  firmware_version?: string;
  priority?: string;
  key_parameters?: RequirementKeyParameter[];
  risk_points?: string;
  tpm_owner_id?: string;
  manual_dev_id?: string;
  auto_dev_id?: string;
  attachments?: Record<string, unknown>[];
}

export interface RequirementResponse {
  id: string;
  req_id: string;
  workflow_item_id?: string;
  title: string;
  description?: string;
  technical_spec?: string;
  target_components: string[];
  firmware_version?: string;
  priority: string;
  key_parameters: RequirementKeyParameter[];
  risk_points?: string;
  tpm_owner_id: string;
  manual_dev_id?: string;
  auto_dev_id?: string;
  status: string;
  attachments: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface ListRequirementsParams {
  status?: string;
  tpm_owner_id?: string;
  manual_dev_id?: string;
  auto_dev_id?: string;
  limit?: number;
  offset?: number;
}

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

export interface CreateTestCaseRequest {
  case_id?: string;
  ref_req_id: string;
  title: string;
  version?: number;
  is_active?: boolean;
  change_log?: string;
  owner_id?: string;
  reviewer_id?: string;
  auto_dev_id?: string;
  priority?: string;
  estimated_duration_sec?: number;
  target_components?: string[];
  required_env?: Record<string, unknown>;
  tags?: string[];
  test_category?: string;
  tooling_req?: string[];
  is_destructive?: boolean;
  pre_condition?: string;
  post_condition?: string;
  cleanup_steps?: TestCaseStep[];
  steps?: TestCaseStep[];
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
}

export interface TestCaseResponse {
  id: string;
  case_id: string;
  ref_req_id: string;
  workflow_item_id?: string;
  title: string;
  version: number;
  is_active: boolean;
  change_log?: string;
  status: string;
  owner_id?: string;
  reviewer_id?: string;
  auto_dev_id?: string;
  priority?: string;
  estimated_duration_sec?: number;
  target_components: string[];
  required_env: Record<string, unknown>;
  tags: string[];
  test_category?: string;
  tooling_req: string[];
  is_destructive: boolean;
  pre_condition?: string;
  post_condition?: string;
  cleanup_steps: TestCaseStep[];
  steps: TestCaseStep[];
  is_need_auto: boolean;
  is_automated: boolean;
  automation_type?: string;
  script_entity_id?: string;
  automation_case_ref?: AutomationCaseRef;
  risk_level?: string;
  failure_analysis?: string;
  confidentiality?: string;
  visibility_scope?: string;
  attachments: Record<string, unknown>[];
  custom_fields: Record<string, unknown>;
  deprecation_reason?: string;
  approval_history: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface ListTestCasesParams {
  ref_req_id?: string;
  status?: string;
  owner_id?: string;
  reviewer_id?: string;
  priority?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export interface DispatchCaseItem {
  auto_case_id: string;
}

export interface DispatchTaskRequest {
  framework: string;
  agent_id?: string;
  trigger_source?: string;
  schedule_type?: string;
  planned_at?: string;
  callback_url?: string;
  dut?: Record<string, unknown>;
  cases: DispatchCaseItem[];
}

export interface DispatchTaskResponse {
  task_id: string;
  external_task_id?: string;
  dispatch_status: string;
  overall_status: string;
  case_count: number;
  created_at: string;
}

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

export interface CreateAutomationTestCaseRequest {
  auto_case_id?: string;
  name: string;
  version?: string;
  status?: string;
  framework?: string;
  automation_type?: string;
  repo_url?: string;
  repo_branch?: string;
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
  name: string;
  version: string;
  status: string;
  framework?: string;
  automation_type?: string;
  repo_url?: string;
  repo_branch?: string;
  script_entity_id?: string;
  entry_command?: string;
  runtime_env: Record<string, unknown>;
  tags: string[];
  maintainer_id?: string;
  reviewer_id?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ListAutomationTestCasesParams {
  framework?: string;
  automation_type?: string;
  status?: string;
  maintainer_id?: string;
  limit?: number;
  offset?: number;
}

export interface ExecutionTask {
  task_id: string;
  external_task_id?: string;
  framework: string;
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
}

export interface TaskStatus {
  task_id: string;
  external_task_id?: string;
  framework: string;
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
  result_summary?: Record<string, unknown>;
}

export interface ListTasksParams {
  schedule_type?: string;
  schedule_status?: string;
  dispatch_status?: string;
  consume_status?: string;
  overall_status?: string;
  created_by?: string;
  agent_id?: string;
  framework?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}
