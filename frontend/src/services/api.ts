import type { LoginRequest, LoginResponse, ApiResponse, CreateRequirementRequest, RequirementResponse, ListRequirementsParams, CreateTestCaseRequest, UpdateTestCaseRequest, TestCaseResponse, TestCaseChangeLogListResponse, ListTestCasesParams, CatalogLab, CreateCatalogLabRequest, UpdateCatalogLabRequest, CatalogTreeResponse, DispatchTaskRequest, DispatchTaskResponse, ExecutionAgent, AgentCleanupOfflineResponse, ListAgentsParams, CreateAutomationTestCaseRequest, AutomationTestCaseResponse, ListAutomationTestCasesParams, ExecutionTask, ListTasksParams, TaskStatus, RerunTaskRequest, AttachmentInfo, WorkflowTransitionRequest, WorkflowTransitionResponse, WorkflowTransitionsResponse, WorkflowTransitionLog, RoleResponse, PermissionResponse, CreateRoleRequest, UpdateRoleRequest, UpdateRolePermissionsRequest, CurrentUserPermissionsResponse, UserResponse, CreateUserRequest, UpdateUserRequest, UpdateUserRolesRequest, UpdateUserPasswordRequest, ListUsersParams, NavigationPageResponse, UserNavigationResponse, UpdateUserNavigationRequest, WorkItem, LineageGraphResponse, CommentListResponse, CreateCommentRequest, TestCaseComment, PlanTaskItemResponse, SubmitManualResultRequest, PlanItemDispatchRequest, BatchDispatchPlanItemsRequest, CreatePlanRequest, AddPlanItemsRequest, UserEffectivePermissionsResponse, UpdateUserExtraPermissionsRequest } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.loadTokenFromStorage();
  }

  private loadTokenFromStorage() {
    const storedToken = localStorage.getItem('jwt_token');
    if (storedToken) {
      this.token = storedToken;
    }
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('jwt_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('jwt_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config: RequestInit = {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let detail = `HTTP error! status: ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody?.data?.detail) {
            detail = errBody.data.detail;
          } else if (errBody?.message) {
            detail = errBody.message;
          }
        } catch {
          // 解析失败就用默认错误消息
        }
        throw new Error(detail);
      }

      // 204 No Content 无响应体，直接返回
      if (response.status === 204) {
        return undefined as unknown as ApiResponse<T>;
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return this.request<LoginResponse['data']>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async listTestCases(params: ListTestCasesParams = {}): Promise<ApiResponse<TestCaseResponse[]>> {
    const queryParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/test-cases${queryString ? `?${queryString}` : ''}`;
    
    return this.request<TestCaseResponse[]>(endpoint, {
      method: 'GET',
    });
  }

  async createTestCase(data: CreateTestCaseRequest): Promise<ApiResponse<TestCaseResponse>> {
    return this.request<TestCaseResponse>('/test-cases', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTestCase(caseId: string): Promise<ApiResponse<TestCaseResponse>> {
    return this.request<TestCaseResponse>(`/test-cases/${caseId}`, {
      method: 'GET',
    });
  }

  async getTestCaseChangeLogs(
    caseId: string,
    params?: { limit?: number; offset?: number },
  ): Promise<ApiResponse<TestCaseChangeLogListResponse>> {
    const searchParams = new URLSearchParams();
    if (params?.limit != null) searchParams.set('limit', String(params.limit));
    if (params?.offset != null) searchParams.set('offset', String(params.offset));
    const qs = searchParams.toString();
    return this.request(`/test-cases/${caseId}/change-logs${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  async updateTestCase(
    caseId: string,
    data: UpdateTestCaseRequest,
  ): Promise<ApiResponse<TestCaseResponse>> {
    return this.request<TestCaseResponse>(`/test-cases/${caseId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTestCase(caseId: string): Promise<ApiResponse<{ deleted: boolean }>> {
    return this.request<{ deleted: boolean }>(`/test-cases/${caseId}`, {
      method: 'DELETE',
    });
  }

  /* ── Test Case Comments ── */
  async listComments(
    caseId: string,
    params?: { limit?: number; offset?: number },
  ): Promise<ApiResponse<CommentListResponse>> {
    const qs = new URLSearchParams()
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    const query = qs.toString()
    return this.request<CommentListResponse>(`/test-cases/${caseId}/comments${query ? `?${query}` : ''}`, {
      method: 'GET',
    });
  }

  async createComment(caseId: string, data: CreateCommentRequest): Promise<ApiResponse<TestCaseComment>> {
    return this.request<TestCaseComment>(`/test-cases/${caseId}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateComment(
    caseId: string,
    commentId: string,
    data: CreateCommentRequest,
  ): Promise<ApiResponse<TestCaseComment>> {
    return this.request<TestCaseComment>(`/test-cases/${caseId}/comments/${commentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteComment(caseId: string, commentId: string): Promise<void> {
    return this.request<void>(`/test-cases/${caseId}/comments/${commentId}`, {
      method: 'DELETE',
    });
  }

  async listRequirements(params: ListRequirementsParams = {}): Promise<ApiResponse<RequirementResponse[]>> {
    const queryParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/requirements${queryString ? `?${queryString}` : ''}`;

    return this.request<RequirementResponse[]>(endpoint, {
      method: 'GET',
    });
  }

  async createRequirement(data: CreateRequirementRequest): Promise<ApiResponse<RequirementResponse>> {
    return this.request<RequirementResponse>('/requirements', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getRequirement(reqId: string): Promise<ApiResponse<RequirementResponse>> {
    return this.request<RequirementResponse>(`/requirements/${reqId}`, {
      method: 'GET',
    });
  }

  async deleteRequirement(reqId: string): Promise<ApiResponse<{ req_id: string; deleted: boolean }>> {
    return this.request<{ req_id: string; deleted: boolean }>(`/requirements/${reqId}`, {
      method: 'DELETE',
    });
  }

  async getWorkflowTransitions(itemId: string): Promise<ApiResponse<WorkflowTransitionsResponse>> {
    return this.request<WorkflowTransitionsResponse>(`/work-items/${itemId}/transitions`, {
      method: 'GET',
    });
  }

  async transitionWorkflow(
    itemId: string,
    data: WorkflowTransitionRequest,
  ): Promise<ApiResponse<WorkflowTransitionResponse>> {
    return this.request<WorkflowTransitionResponse>(`/work-items/${itemId}/transition`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWorkflowLogs(
    itemId: string,
    limit = 50,
  ): Promise<ApiResponse<WorkflowTransitionLog[]>> {
    return this.request<WorkflowTransitionLog[]>(
      `/work-items/${itemId}/logs?limit=${limit}`,
      { method: 'GET' },
    );
  }

  async reassignWorkItem(
    itemId: string,
    targetOwnerId: string,
    remark?: string,
  ): Promise<ApiResponse<WorkItem>> {
    const params = new URLSearchParams({ target_owner_id: targetOwnerId });
    if (remark?.trim()) {
      params.append('remark', remark.trim());
    }
    return this.request<WorkItem>(`/work-items/${itemId}/reassign?${params.toString()}`, {
      method: 'POST',
    });
  }

  async listMyWorkItems(userId: string): Promise<ApiResponse<WorkItem[]>> {
    return this.request<WorkItem[]>(`/work-items/sorted?owner_id=${userId}&order_by=updated_at&direction=desc&limit=100`, {
      method: 'GET',
    });
  }

  async uploadAttachment(file: File): Promise<AttachmentInfo> {
    const url = `${this.baseUrl}/attachments/upload`;
    const formData = new FormData();
    formData.append('file', file);

    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Attachment upload failed:', error);
      throw error;
    }
  }

  async dispatchTask(data: DispatchTaskRequest): Promise<ApiResponse<DispatchTaskResponse>> {
    return this.request<DispatchTaskResponse>('/execution/tasks/dispatch', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async rerunTask(taskId: string, data: RerunTaskRequest = {}): Promise<ApiResponse<DispatchTaskResponse>> {
    return this.request<DispatchTaskResponse>(`/execution/tasks/${taskId}/rerun`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listAgents(params: ListAgentsParams = {}): Promise<ApiResponse<ExecutionAgent[]>> {
    const queryParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/execution/agents${queryString ? `?${queryString}` : ''}`;
    
    return this.request<ExecutionAgent[]>(endpoint, {
      method: 'GET',
    });
  }

  async getAgent(agentId: string): Promise<ApiResponse<ExecutionAgent>> {
    return this.request<ExecutionAgent>(`/execution/agents/${agentId}`, {
      method: 'GET',
    });
  }

  async deleteAgent(agentId: string): Promise<ApiResponse<{ agent_id: string; deleted: boolean }>> {
    return this.request<{ agent_id: string; deleted: boolean }>(`/execution/agents/${agentId}`, {
      method: 'DELETE',
    });
  }

  async cleanupOfflineAgents(): Promise<ApiResponse<AgentCleanupOfflineResponse>> {
    return this.request<AgentCleanupOfflineResponse>('/execution/agents/cleanup-offline', {
      method: 'POST',
    });
  }

  async createAutomationTestCase(data: CreateAutomationTestCaseRequest): Promise<ApiResponse<AutomationTestCaseResponse>> {
    return this.request<AutomationTestCaseResponse>('/automation-test-cases', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listAutomationTestCases(params: ListAutomationTestCasesParams = {}): Promise<ApiResponse<AutomationTestCaseResponse[]>> {
    const queryParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/automation-test-cases${queryString ? `?${queryString}` : ''}`;
    
    return this.request<AutomationTestCaseResponse[]>(endpoint, {
      method: 'GET',
    });
  }

  async getAutomationTestCase(autoCaseId: string): Promise<ApiResponse<AutomationTestCaseResponse>> {
    return this.request<AutomationTestCaseResponse>(`/automation-test-cases/${autoCaseId}`, {
      method: 'GET',
    });
  }

  async deleteAutomationTestCase(autoCaseId: string): Promise<ApiResponse<{ deleted: boolean }>> {
    return this.request<{ deleted: boolean }>(`/automation-test-cases/${autoCaseId}`, {
      method: 'DELETE',
    });
  }

  async listTasks(params: ListTasksParams = {}): Promise<ApiResponse<ExecutionTask[]>> {
    const queryParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/execution/tasks${queryString ? `?${queryString}` : ''}`;

    return this.request<ExecutionTask[]>(endpoint, {
      method: 'GET',
    });
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return this.request<TaskStatus>(`/execution/tasks/${taskId}/status`, {
      method: 'GET',
    });
  }

  async deleteTask(taskId: string): Promise<ApiResponse<{ task_id: string; deleted: boolean }>> {
    return this.request<{ task_id: string; deleted: boolean }>(`/execution/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  // Role and Permission APIs
  async listRoles(): Promise<ApiResponse<RoleResponse[]>> {
    return this.request<RoleResponse[]>('/auth/roles', {
      method: 'GET',
    });
  }

  async getRole(roleId: string): Promise<ApiResponse<RoleResponse>> {
    return this.request<RoleResponse>(`/auth/roles/${roleId}`, {
      method: 'GET',
    });
  }

  async createRole(data: CreateRoleRequest): Promise<ApiResponse<RoleResponse>> {
    return this.request<RoleResponse>('/auth/roles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateRole(roleId: string, data: UpdateRoleRequest): Promise<ApiResponse<RoleResponse>> {
    return this.request<RoleResponse>(`/auth/roles/${roleId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async updateRolePermissions(roleId: string, data: UpdateRolePermissionsRequest): Promise<ApiResponse<RoleResponse>> {
    return this.request<RoleResponse>(`/auth/roles/${roleId}/permissions`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteRole(roleId: string): Promise<void> {
    await this.request<void>(`/auth/roles/${roleId}`, {
      method: 'DELETE',
    });
  }

  async listPermissions(): Promise<ApiResponse<PermissionResponse[]>> {
    return this.request<PermissionResponse[]>('/auth/permissions', {
      method: 'GET',
    });
  }

  async createPermission(data: { perm_id: string; code: string; name: string; description?: string }): Promise<ApiResponse<PermissionResponse>> {
    return this.request<PermissionResponse>('/auth/permissions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deletePermission(permId: string): Promise<void> {
    await this.request<void>(`/auth/permissions/${permId}`, {
      method: 'DELETE',
    });
  }

  async updatePermission(permId: string, data: { name?: string; description?: string }): Promise<ApiResponse<PermissionResponse>> {
    return this.request<PermissionResponse>(`/auth/permissions/${permId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getCurrentUserPermissions(): Promise<ApiResponse<CurrentUserPermissionsResponse>> {
    return this.request<CurrentUserPermissionsResponse>('/auth/users/me/permissions', {
      method: 'GET',
    });
  }

  async getCurrentUser(): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>('/auth/users/me', {
      method: 'GET',
    });
  }

  // User APIs
  async listUsers(params: ListUsersParams = {}): Promise<ApiResponse<UserResponse[]>> {
    const queryParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/auth/users${queryString ? `?${queryString}` : ''}`;

    return this.request<UserResponse[]>(endpoint, {
      method: 'GET',
    });
  }

  async getUser(userId: string): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>(`/auth/users/${userId}`, {
      method: 'GET',
    });
  }

  async createUser(data: CreateUserRequest): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>('/auth/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(userId: string, data: UpdateUserRequest): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>(`/auth/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async updateUserRoles(userId: string, data: UpdateUserRolesRequest): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>(`/auth/users/${userId}/roles`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async updateUserPassword(userId: string, data: UpdateUserPasswordRequest): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>(`/auth/users/${userId}/password`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(userId: string): Promise<void> {
    await this.request<void>(`/auth/users/${userId}`, {
      method: 'DELETE',
    });
  }

  async getUserEffectivePermissions(userId: string): Promise<ApiResponse<UserEffectivePermissionsResponse>> {
    return this.request<UserEffectivePermissionsResponse>(`/auth/users/${userId}/permissions`, {
      method: 'GET',
    });
  }

  async updateUserExtraPermissions(userId: string, data: UpdateUserExtraPermissionsRequest): Promise<ApiResponse<UserResponse>> {
    return this.request<UserResponse>(`/auth/users/${userId}/permissions/extra`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async listNavigationPages(params: { include_inactive?: boolean } = {}): Promise<ApiResponse<NavigationPageResponse[]>> {
    const query = new URLSearchParams();
    if (params.include_inactive === false) {
      query.append('include_inactive', 'false');
    }
    const qs = query.toString();
    return this.request<NavigationPageResponse[]>(
      `/auth/admin/navigation/pages${qs ? `?${qs}` : ''}`,
      { method: 'GET' },
    );
  }

  async getUserNavigation(userId: string): Promise<ApiResponse<UserNavigationResponse>> {
    return this.request<UserNavigationResponse>(`/auth/admin/users/${userId}/navigation`, {
      method: 'GET',
    });
  }

  async updateUserNavigation(
    userId: string,
    data: UpdateUserNavigationRequest,
  ): Promise<ApiResponse<UserNavigationResponse>> {
    return this.request<UserNavigationResponse>(`/auth/admin/users/${userId}/navigation`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Catalog Lab APIs
  async listCatalogLabs(params: { active_only?: boolean } = {}): Promise<ApiResponse<CatalogLab[]>> {
    const query = new URLSearchParams();
    if (params.active_only) {
      query.append('active_only', 'true');
    }
    const qs = query.toString();
    return this.request<CatalogLab[]>(`/catalog/labs${qs ? `?${qs}` : ''}`, { method: 'GET' });
  }

  async createCatalogLab(data: CreateCatalogLabRequest): Promise<ApiResponse<CatalogLab>> {
    return this.request<CatalogLab>('/catalog/labs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCatalogLab(labId: string, data: UpdateCatalogLabRequest): Promise<ApiResponse<CatalogLab>> {
    return this.request<CatalogLab>(`/catalog/labs/${labId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deactivateCatalogLab(
    labId: string,
    targetLabId: string,
  ): Promise<ApiResponse<CatalogLab>> {
    return this.request<CatalogLab>(`/catalog/labs/${labId}/deactivate`, {
      method: 'POST',
      body: JSON.stringify({ target_lab_id: targetLabId }),
    });
  }

  async deleteCatalogLab(labId: string): Promise<void> {
    await this.request<void>(`/catalog/labs/${labId}`, { method: 'DELETE' });
  }

  async getCatalogSuggestions(
    labId: string,
    parentPath: string[] = [],
  ): Promise<ApiResponse<{ lab_id: string; parent_path: string[]; segments: string[] }>> {
    const query = new URLSearchParams({ lab_id: labId });
    if (parentPath.length > 0) {
      query.append('parent_path', JSON.stringify(parentPath));
    }
    return this.request(`/catalog/suggestions?${query.toString()}`, { method: 'GET' });
  }

  async getCatalogTree(labId: string): Promise<ApiResponse<CatalogTreeResponse>> {
    return this.request<CatalogTreeResponse>(`/catalog/tree?lab_id=${encodeURIComponent(labId)}`, {
      method: 'GET',
    });
  }

  // === Lineage Graph API ===
  async getLineageGraph(entityType: string, entityId: string, maxNodes = 50): Promise<ApiResponse<LineageGraphResponse>> {
    const params = new URLSearchParams({ entity_type: entityType, entity_id: entityId, max_nodes: String(maxNodes) });
    return this.request<LineageGraphResponse>(`/lineage/graph?${params.toString()}`, { method: 'GET' });
  }

  // ── Global Search ────────────────────────────────────────────────

  async search(q: string, options?: { types?: string; limit?: number; offset?: number }): Promise<ApiResponse<SearchResponse>> {
    const params = new URLSearchParams({ q });
    if (options?.types) params.set('types', options.types);
    if (options?.limit) params.set('limit', String(options.limit));
    if (options?.offset) params.set('offset', String(options.offset));
    return this.request<SearchResponse>(`/search?${params.toString()}`, { method: 'GET' });
  }

  // ── TestCaseCollection ──────────────────────────────────────────

  async listCollections(q?: string): Promise<ApiResponse<CollectionListItem[]>> {
    const params = q ? `?${new URLSearchParams({ q }).toString()}` : '';
    return this.request<CollectionListItem[]>(`/collections${params}`, { method: 'GET' });
  }

  async searchCollections(q: string, limit = 10): Promise<ApiResponse<CollectionListItem[]>> {
    const params = new URLSearchParams({ q, limit: String(limit) });
    return this.request<CollectionListItem[]>(`/collections/search?${params.toString()}`, { method: 'GET' });
  }

  async getCollection(id: string): Promise<ApiResponse<CollectionResponse>> {
    return this.request<CollectionResponse>(`/collections/${id}`, { method: 'GET' });
  }

  async createCollection(data: CreateCollectionRequest): Promise<ApiResponse<CollectionResponse>> {
    return this.request<CollectionResponse>('/collections', {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async updateCollection(id: string, data: UpdateCollectionRequest): Promise<ApiResponse<CollectionResponse>> {
    return this.request<CollectionResponse>(`/collections/${id}`, {
      method: 'PUT', body: JSON.stringify(data),
    });
  }

  async deleteCollection(id: string): Promise<ApiResponse<{ deleted: string }>> {
    return this.request<{ deleted: string }>(`/collections/${id}`, { method: 'DELETE' });
  }

  async addCasesToCollection(id: string, data: AddCasesRequest): Promise<ApiResponse<CollectionResponse>> {
    return this.request<CollectionResponse>(`/collections/${id}/cases`, {
      method: 'POST', body: JSON.stringify(data),
    });
  }

  async removeCasesFromCollection(id: string, data: RemoveCasesRequest): Promise<ApiResponse<CollectionResponse>> {
    return this.request<CollectionResponse>(`/collections/${id}/cases`, {
      method: 'DELETE', body: JSON.stringify(data),
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  执行计划 / My Tasks API
  // ══════════════════════════════════════════════════════════════

  /** 获取当前用户的计划任务列表 */
  async listMyPlanItems(assigneeId: string): Promise<ApiResponse<PlanTaskItemResponse[]>> {
    return this.request<PlanTaskItemResponse[]>(
      `/execution-plans/items/my-items?assignee_id=${encodeURIComponent(assigneeId)}`,
      { method: 'GET' },
    );
  }

  /** 更新计划条目（状态/指派人等） */
  async updatePlanItem(
    planId: string,
    itemId: string,
    data: { status?: string; assignee_id?: string; component?: string },
  ): Promise<ApiResponse<PlanTaskItemResponse>> {
    return this.request<PlanTaskItemResponse>(`/execution-plans/plans/${planId}/items/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /** 提交手工测试结果回填 */
  async submitPlanItemResult(
    itemId: string,
    data: SubmitManualResultRequest,
  ): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/items/${itemId}/result`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** 获取已有的手工结果回填 */
  async getPlanItemResult(itemId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/items/${itemId}/result`, {
      method: 'GET',
    });
  }

  /** 单条自动化用例计划内下发 */
  async dispatchPlanItem(
    itemId: string,
    data: PlanItemDispatchRequest,
  ): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/items/${itemId}/dispatch`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** 批量下发自动化用例 */
  async batchDispatchPlanItems(
    data: BatchDispatchPlanItemsRequest,
  ): Promise<ApiResponse<Array<Record<string, unknown>>>> {
    return this.request<Array<Record<string, unknown>>>('/execution-plans/items/batch-dispatch', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  执行计划 — Plan CRUD
  // ══════════════════════════════════════════════════════════════

  /** 获取执行计划列表 */
  async listPlans(status?: string): Promise<ApiResponse<Array<Record<string, unknown>>>> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return this.request<Array<Record<string, unknown>>>(`/execution-plans/plans${query}`, {
      method: 'GET',
    });
  }

  /** 创建执行计划 */
  async createPlan(data: CreatePlanRequest): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>('/execution-plans/plans', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** 获取执行计划详情（含条目） */
  async getPlanDetail(planId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/plans/${encodeURIComponent(planId)}`, {
      method: 'GET',
    });
  }

  /** 更新执行计划 */
  async updatePlan(planId: string, data: Record<string, unknown>): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/plans/${encodeURIComponent(planId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /** 删除执行计划 */
  async deletePlan(planId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/plans/${encodeURIComponent(planId)}`, {
      method: 'DELETE',
    });
  }

  /** 为执行计划添加条目 */
  async addPlanItems(planId: string, data: AddPlanItemsRequest): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/plans/${encodeURIComponent(planId)}/items`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** 从执行计划中移除条目 */
  async deletePlanItem(planId: string, itemId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/plans/${encodeURIComponent(planId)}/items/${encodeURIComponent(itemId)}`, {
      method: 'DELETE',
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  收纳箱 API
  // ══════════════════════════════════════════════════════════════

  /** 获取已归档的计划任务列表（收纳箱） */
  async listArchivedItems(assigneeId: string): Promise<ApiResponse<PlanTaskItemResponse[]>> {
    return this.request<PlanTaskItemResponse[]>(
      `/execution-plans/items/archived?assignee_id=${encodeURIComponent(assigneeId)}`,
      { method: 'GET' },
    );
  }

  /** 归档计划条目（收纳） */
  async archiveItem(itemId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/items/${encodeURIComponent(itemId)}/archive`, {
      method: 'PUT',
    });
  }

  /** 取消归档计划条目 */
  async unarchiveItem(itemId: string): Promise<ApiResponse<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(`/execution-plans/items/${encodeURIComponent(itemId)}/unarchive`, {
      method: 'PUT',
    });
  }
}

export const api = new ApiClient(API_BASE_URL);
