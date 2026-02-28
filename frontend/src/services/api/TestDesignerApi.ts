/**
 * @fileoverview 测试设计器API服务类
 * 封装所有后端API调用方法，按功能模块组织
 */

import { CreateRequirementPayload, CreateTestCasePayload, TestCase, TestRequirement } from '../../types';
import { User } from '../../constants/config';
import { ApiClient } from './ApiClient';

// ========== 响应数据类型定义 ==========

/**
 * 登录响应接口
 */
interface LoginResponse {
  access_token: string;  // JWT访问令牌
  token_type: string;    // 令牌类型（通常为"Bearer"）
  user: User;           // 用户信息
}

/**
 * 用户权限响应接口
 */
interface MePermissionsResponse {
  user_id: string;       // 用户ID
  role_ids: string[];    // 角色ID列表
  permissions: string[]; // 权限代码列表
}

/**
 * 导航页面配置接口
 */
interface NavigationPage {
  view: string;           // 视图名称
  label: string;          // 显示标签
  permission: string;     // 所需权限
  description?: string;   // 页面描述
}

/**
 * 导航访问权限响应接口
 */
interface NavigationAccessResponse {
  user_id?: string;           // 用户ID（可选）
  allowed_nav_views?: string[]; // 允许访问的导航视图
  nav_views?: string[];        // 导航视图列表
  views?: string[];            // 视图列表
}

/**
 * 测试设计器API服务类
 * 统一管理所有后端API接口，按功能分为认证、需求、用例、用户管理四大模块
 */
export class TestDesignerApi {
  /**
   * 构造函数
   * @param client HTTP客户端实例
   */
  constructor(private readonly client: ApiClient) {}

  // ========== 认证模块 API ==========

  /**
   * 用户登录
   * 使用用户名和密码获取访问令牌
   * @param user_id 用户ID
   * @param password 密码
   * @returns Promise<LoginResponse> 包含访问令牌和用户信息
   */
  async login(user_id: string, password: string): Promise<LoginResponse> {
    return this.client.post<LoginResponse>('/api/v1/auth/login', {
      user_id,
      password
    });
  }

  /**
   * 获取当前用户信息
   * 基于已保存的访问令牌获取用户详情
   * @returns Promise<User> 当前用户完整信息
   */
  async getCurrentUser(): Promise<User> {
    return this.client.get<User>('/api/v1/auth/users/me');
  }

  /**
   * 获取当前用户权限列表
   * 返回用户的所有权限代码和角色信息
   * @returns Promise<MePermissionsResponse> 权限响应对象
   */
  async getMyPermissions(): Promise<MePermissionsResponse> {
    return this.client.get<MePermissionsResponse>('/api/v1/auth/users/me/permissions');
  }

  /**
   * 获取当前用户可访问的导航页面
   * 基于用户权限返回可见的导航菜单项
   * @returns Promise<NavigationAccessResponse | string[]> 导航配置
   */
  async getMyNavigation(): Promise<NavigationAccessResponse | string[]> {
    return this.client.get<NavigationAccessResponse | string[]>('/api/v1/auth/users/me/navigation');
  }

  /**
   * 修改当前用户密码
   * @param old_password 当前密码
   * @param new_password 新密码
   * @returns Promise<User> 更新后的用户信息
   */
  async changePassword(old_password: string, new_password: string): Promise<User> {
    return this.client.post<User>('/api/v1/auth/users/me/password', {
      old_password,
      new_password
    });
  }

  // ========== 测试需求管理模块 API ==========

  /**
   * 获取所有测试需求列表
   * @returns Promise<TestRequirement[]> 需求数组
   */
  listRequirements(): Promise<TestRequirement[]> {
    return this.client.get<TestRequirement[]>('/api/v1/requirements');
  }

  /**
   * 获取指定需求详情
   * @param reqId 需求ID
   * @returns Promise<TestRequirement> 需求详细信息
   */
  getRequirement(reqId: string): Promise<TestRequirement> {
    return this.client.get<TestRequirement>(`/api/v1/requirements/${reqId}`);
  }

  /**
   * 创建新的测试需求
   * @param payload 创建需求的数据载荷
   * @returns Promise<TestRequirement> 创建的需求对象
   */
  createRequirement(payload: CreateRequirementPayload): Promise<TestRequirement> {
    return this.client.post<TestRequirement>('/api/v1/requirements', payload);
  }

  /**
   * 更新现有测试需求
   * @param reqId 需求ID
   * @param payload 更新数据
   * @returns Promise<TestRequirement> 更新后的需求对象
   */
  updateRequirement(reqId: string, payload: TestRequirement): Promise<TestRequirement> {
    return this.client.put<TestRequirement>(`/api/v1/requirements/${reqId}`, payload);
  }

  /**
   * 删除测试需求
   * @param reqId 需求ID
   * @returns Promise<void>
   */
  deleteRequirement(reqId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/requirements/${reqId}`);
  }

  // ========== 测试用例管理模块 API ==========

  /**
   * 获取所有测试用例列表
   * @returns Promise<TestCase[]> 用例数组
   */
  listTestCases(): Promise<TestCase[]> {
    return this.client.get<TestCase[]>('/api/v1/test-cases');
  }

  /**
   * 获取指定测试用例详情
   * @param caseId 用例ID
   * @returns Promise<TestCase> 用例详细信息
   */
  getTestCase(caseId: string): Promise<TestCase> {
    return this.client.get<TestCase>(`/api/v1/test-cases/${caseId}`);
  }

  /**
   * 创建新的测试用例
   * @param payload 创建用例的数据载荷
   * @returns Promise<TestCase> 创建的用例对象
   */
  createTestCase(payload: CreateTestCasePayload): Promise<TestCase> {
    return this.client.post<TestCase>('/api/v1/test-cases', payload);
  }

  /**
   * 更新现有测试用例
   * @param caseId 用例ID
   * @param payload 更新数据
   * @returns Promise<TestCase> 更新后的用例对象
   */
  updateTestCase(caseId: string, payload: TestCase): Promise<TestCase> {
    return this.client.put<TestCase>(`/api/v1/test-cases/${caseId}`, payload);
  }

  /**
   * 删除测试用例
   * @param caseId 用例ID
   * @returns Promise<void>
   */
  deleteTestCase(caseId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/test-cases/${caseId}`);
  }

  // ========== 用户管理模块 API ==========

  /**
   * 获取所有用户列表
   * @returns Promise<User[]> 用户数组
   */
  listUsers(): Promise<User[]> {
    return this.client.get<User[]>('/api/v1/auth/users');
  }

  /**
   * 获取指定用户详情
   * @param userId 用户ID
   * @returns Promise<User> 用户信息
   */
  getUser(userId: string): Promise<User> {
    return this.client.get<User>(`/api/v1/auth/users/${userId}`);
  }

  /**
   * 创建新用户
   * @param payload 用户数据
   * @returns Promise<User> 创建的用户对象
   */
  createUser(payload: User): Promise<User> {
    return this.client.post<User>('/api/v1/auth/users', payload);
  }

  /**
   * 更新用户信息
   * @param userId 用户ID
   * @param payload 更新数据（部分字段）
   * @returns Promise<User> 更新后的用户对象
   */
  updateUser(userId: string, payload: Partial<User>): Promise<User> {
    return this.client.put<User>(`/api/v1/auth/users/${userId}`, payload);
  }

  /**
   * 删除用户
   * @param userId 用户ID
   * @returns Promise<void>
   */
  deleteUser(userId: string): Promise<void> {
    return this.client.delete<void>(`/api/v1/auth/users/${userId}`);
  }

  // ========== 管理员专用 API ==========

  /**
   * 获取系统导航页面定义
   * 返回系统中所有可配置的导航页面
   * @returns Promise<NavigationPage[] | { pages?: NavigationPage[] }> 导航页面配置
   */
  getNavigationPages(): Promise<NavigationPage[] | { pages?: NavigationPage[] }> {
    return this.client.get<NavigationPage[] | { pages?: NavigationPage[] }>('/api/v1/auth/admin/navigation/pages');
  }

  /**
   * 获取指定用户的导航权限
   * 管理员可查看任意用户的导航页面访问权限
   * @param userId 用户ID
   * @returns Promise<NavigationAccessResponse | string[]> 导航权限信息
   */
  getUserNavigation(userId: string): Promise<NavigationAccessResponse | string[]> {
    return this.client.get<NavigationAccessResponse | string[]>(`/api/v1/auth/admin/users/${userId}/navigation`);
  }

  /**
   * 更新指定用户的导航权限
   * 管理员可修改任意用户的导航页面访问权限
   * @param userId 用户ID
   * @param allowedNavViews 允许访问的导航视图列表
   * @returns Promise<NavigationAccessResponse | User> 更新结果
   */
  updateUserNavigation(userId: string, allowedNavViews: string[]): Promise<NavigationAccessResponse | User> {
    return this.client.put<NavigationAccessResponse | User>(`/api/v1/auth/admin/users/${userId}/navigation`, {
      allowed_nav_views: allowedNavViews,
    });
  }
}
