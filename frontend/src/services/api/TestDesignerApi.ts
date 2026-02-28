import { CreateRequirementPayload, CreateTestCasePayload, TestCase, TestRequirement } from '../../types';
import { User } from '../../constants/config';
import { ApiClient } from './ApiClient';

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface MePermissionsResponse {
  user_id: string;
  role_ids: string[];
  permissions: string[];
}

interface NavigationPage {
  view: string;
  label: string;
  permission: string;
  description?: string;
}

interface NavigationAccessResponse {
  user_id?: string;
  allowed_nav_views?: string[];
  nav_views?: string[];
  views?: string[];
}

export class TestDesignerApi {
  constructor(private readonly client: ApiClient) {}

  // ========== 认证相关 API ==========

  /**
   * 用户登录
   */
  async login(user_id: string, password: string): Promise<LoginResponse> {
    return this.client.post<LoginResponse>('/api/v1/auth/login', {
      user_id,
      password
    });
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    return this.client.get<User>('/api/v1/auth/users/me');
  }

  /**
   * 获取当前用户权限
   */
  async getMyPermissions(): Promise<MePermissionsResponse> {
    return this.client.get<MePermissionsResponse>('/api/v1/auth/users/me/permissions');
  }

  /**
   * 获取当前用户可访问的导航页面
   */
  async getMyNavigation(): Promise<NavigationAccessResponse | string[]> {
    return this.client.get<NavigationAccessResponse | string[]>('/api/v1/auth/users/me/navigation');
  }

  /**
   * 修改密码
   */
  async changePassword(old_password: string, new_password: string): Promise<User> {
    return this.client.post<User>('/api/v1/auth/users/me/password', {
      old_password,
      new_password
    });
  }

  // ========== 需求管理 API ==========

  listRequirements(): Promise<TestRequirement[]> {
    return this.client.get<TestRequirement[]>('/api/v1/requirements');
  }

  getRequirement(reqId: string): Promise<TestRequirement> {
    return this.client.get<TestRequirement>(`/api/v1/requirements/${reqId}`);
  }

  createRequirement(payload: CreateRequirementPayload): Promise<TestRequirement> {
    return this.client.post<TestRequirement>('/api/v1/requirements', payload);
  }

  updateRequirement(reqId: string, payload: TestRequirement): Promise<TestRequirement> {
    return this.client.put<TestRequirement>(`/api/v1/requirements/${reqId}`, payload);
  }

  deleteRequirement(reqId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/requirements/${reqId}`);
  }

  // ========== 测试用例管理 API ==========

  listTestCases(): Promise<TestCase[]> {
    return this.client.get<TestCase[]>('/api/v1/test-cases');
  }

  getTestCase(caseId: string): Promise<TestCase> {
    return this.client.get<TestCase>(`/api/v1/test-cases/${caseId}`);
  }

  createTestCase(payload: CreateTestCasePayload): Promise<TestCase> {
    return this.client.post<TestCase>('/api/v1/test-cases', payload);
  }

  updateTestCase(caseId: string, payload: TestCase): Promise<TestCase> {
    return this.client.put<TestCase>(`/api/v1/test-cases/${caseId}`, payload);
  }

  deleteTestCase(caseId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/test-cases/${caseId}`);
  }

  // ========== 用户管理 API ==========

  listUsers(): Promise<User[]> {
    return this.client.get<User[]>('/api/v1/auth/users');
  }

  getUser(userId: string): Promise<User> {
    return this.client.get<User>(`/api/v1/auth/users/${userId}`);
  }

  createUser(payload: User): Promise<User> {
    return this.client.post<User>('/api/v1/auth/users', payload);
  }

  updateUser(userId: string, payload: Partial<User>): Promise<User> {
    return this.client.put<User>(`/api/v1/auth/users/${userId}`, payload);
  }

  deleteUser(userId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/auth/users/${userId}`);
  }

  /**
   * 获取系统导航定义（管理员）
   */
  getNavigationPages(): Promise<NavigationPage[] | { pages?: NavigationPage[] }> {
    return this.client.get<NavigationPage[] | { pages?: NavigationPage[] }>('/api/v1/auth/admin/navigation/pages');
  }

  /**
   * 获取指定用户导航权限（管理员）
   */
  getUserNavigation(userId: string): Promise<NavigationAccessResponse | string[]> {
    return this.client.get<NavigationAccessResponse | string[]>(`/api/v1/auth/admin/users/${userId}/navigation`);
  }

  /**
   * 更新指定用户导航权限（管理员）
   */
  updateUserNavigation(userId: string, allowedNavViews: string[]): Promise<NavigationAccessResponse | User> {
    return this.client.put<NavigationAccessResponse | User>(`/api/v1/auth/admin/users/${userId}/navigation`, {
      allowed_nav_views: allowedNavViews,
    });
  }
}
