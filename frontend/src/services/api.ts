import type { LoginRequest, LoginResponse, ApiResponse, CreateRequirementRequest, RequirementResponse, ListRequirementsParams, CreateTestCaseRequest, TestCaseResponse, ListTestCasesParams, DispatchTaskRequest, DispatchTaskResponse, ExecutionAgent, ListAgentsParams, CreateAutomationTestCaseRequest, AutomationTestCaseResponse, ListAutomationTestCasesParams, ExecutionTask, ListTasksParams, TaskStatus } from '../types';

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
        throw new Error(`HTTP error! status: ${response.status}`);
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

  async dispatchTask(data: DispatchTaskRequest): Promise<ApiResponse<DispatchTaskResponse>> {
    return this.request<DispatchTaskResponse>('/execution/tasks/dispatch', {
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
}

export const api = new ApiClient(API_BASE_URL);
