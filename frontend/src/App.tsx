/**
 * @fileoverview 主应用组件
 * 服务器测试用例设计器 - 单文件组件架构
 * 集成登录、需求管理、用例管理、用户管理等功能的完整前端应用
 */

import React, { useState, useCallback, useEffect } from 'react';

// ========== 类型导入 ==========
import {
  CreateRequirementPayload,
  CreateTestCasePayload,
  TestCase,
  TestCaseStatus,
  Priority,
  RiskLevel,
  VisibilityScope,
  TestStep,
  TestCaseCategory,
  Confidentiality,
  TestRequirement,
  RequirementStatus,
  Attachment
} from './types';
import { ROLES, User } from './constants/config';

// ========== Hook导入 ==========
import { useLocalAI } from './components/hooks/useLocalAI';

// ========== API服务导入 ==========
import { isBackendEnabled, testDesignerApi, setAccessToken, clearAccessToken } from './services/api';

// ========== 视图组件导入 ==========
import { Login, ReqList, ReqForm, ReqDetail, CaseList, CaseForm, UserMgmt } from './components/views';

// ========== 图标库导入 ==========
import {
  FileText,      // 文档图标（需求列表）
  PlayCircle,    // 播放图标（用例列表）
  User as UserIcon, // 用户图标（用户管理）
  LogIn,         // 登录图标
  Mail,          // 邮件图标
  Calendar,      // 日历图标
  Shield,        // 盾牌图标
  X,             // 关闭图标
} from 'lucide-react';

// ========== 类型定义 ==========

/**
 * 视图类型定义
 * 控制应用中不同页面视图的切换
 */
type View =
  | 'login'        // 登录页面
  | 'req_list'     // 需求列表
  | 'req_form'     // 需求表单（创建/编辑）
  | 'req_detail'   // 需求详情
  | 'case_list'    // 用例列表
  | 'case_form'    // 用例表单（创建/编辑）
  | 'user_mgmt';   // 用户管理

/**
 * 导航视图类型定义
 * 可在主导航菜单中访问的页面
 */
type NavView = 'req_list' | 'case_list' | 'user_mgmt';

/**
 * 导航选项接口
 * 定义导航菜单项的配置信息
 */
interface NavigationOption {
  view: NavView;       // 视图名称
  label: string;       // 显示标签
  permission: string;  // 所需权限代码
  description: string; // 描述信息
}

// ========== 导航配置常量 ==========

/**
 * 系统导航选项配置
 * 定义主导航菜单中可用的页面及其权限要求
 */
const NAVIGATION_OPTIONS: NavigationOption[] = [
  {
    view: 'req_list',
    label: '测试需求',
    permission: 'nav:req_list:view',
    description: '允许访问测试需求列表页'
  },
  {
    view: 'case_list',
    label: '测试用例',
    permission: 'nav:case_list:view',
    description: '允许访问测试用例列表页'
  },
  {
    view: 'user_mgmt',
    label: '用户管理',
    permission: 'nav:user_mgmt:view',
    description: '允许访问用户与权限管理页'
  },
];

/**
 * 导航视图集合
 * 用于快速检查字符串是否为有效的导航视图
 */
const NAV_VIEW_SET = new Set<NavView>(NAVIGATION_OPTIONS.map(item => item.view));

/**
 * 导航视图到权限的映射表
 * 便于根据视图快速获取对应的权限代码
 */
const NAV_VIEW_PERMISSION_MAP: Record<NavView, string> = NAVIGATION_OPTIONS
  .reduce((acc, item) => ({ ...acc, [item.view]: item.permission }), {} as Record<NavView, string>);

/**
 * 默认导航视图
 * 当用户无特定权限时显示的基础导航项
 */
const FALLBACK_NAV_VIEWS: NavView[] = ['req_list', 'case_list'];

// ========== 辅助函数 ==========

/**
 * 检查值是否为有效的导航视图
 * @param value 要检查的值
 * @returns boolean 是否为NavView类型
 */
const isNavView = (value: string): value is NavView => NAV_VIEW_SET.has(value as NavView);

/**
 * 检查用户是否具有管理员角色
 * @param user 用户对象
 * @returns boolean 是否为管理员
 */
const hasAdminRole = (user: User | null): boolean =>
  Boolean(user?.role_ids.some(role => String(role).toUpperCase().includes('ADMIN')));

const sanitizeNavViews = (views: unknown): NavView[] => {
  if (!Array.isArray(views)) {
    return [];
  }
  const unique = new Set<NavView>();
  views.forEach(item => {
    const view = String(item) as NavView;
    if (isNavView(view)) {
      unique.add(view);
    }
  });
  return NAVIGATION_OPTIONS.map(item => item.view).filter(view => unique.has(view));
};

const normalizePermissionCodes = (input: unknown): string[] => {
  if (Array.isArray(input)) {
    return input.map(item => String(item));
  }
  const row = asObject(input);
  if (Array.isArray(row.permissions)) {
    return row.permissions.map(item => String(item));
  }
  return [];
};

const normalizeNavigationViews = (input: unknown): NavView[] => {
  if (Array.isArray(input)) {
    return sanitizeNavViews(input);
  }
  const row = asObject(input);
  if (Array.isArray(row.allowed_nav_views)) return sanitizeNavViews(row.allowed_nav_views);
  if (Array.isArray(row.nav_views)) return sanitizeNavViews(row.nav_views);
  if (Array.isArray(row.views)) return sanitizeNavViews(row.views);
  return [];
};

const deriveNavViewsFromPermissions = (permissions: string[]): NavView[] => {
  if (permissions.includes('all')) {
    return NAVIGATION_OPTIONS.map(item => item.view);
  }
  const matchedViews = NAVIGATION_OPTIONS
    .filter(item => permissions.includes(item.permission))
    .map(item => item.view);
  return sanitizeNavViews(matchedViews);
};

const getDefaultNavViewsForUser = (user: User | null): NavView[] => {
  if (!user) {
    return FALLBACK_NAV_VIEWS;
  }
  if (hasAdminRole(user)) {
    return NAVIGATION_OPTIONS.map(item => item.view);
  }
  return FALLBACK_NAV_VIEWS;
};

const unwrapApiData = <T,>(payload: T | { data?: T } | null | undefined): T | undefined => {
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return (payload as { data?: T }).data;
  }
  return payload as T | undefined;
};

const asObject = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' ? (value as Record<string, unknown>) : {};

const extractList = (input: unknown): unknown[] => {
  if (Array.isArray(input)) return input;
  const row = asObject(input);
  if (Array.isArray(row.items)) return row.items;
  if (Array.isArray(row.results)) return row.results;
  if (Array.isArray(row.data)) return row.data;
  return [];
};

const toArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

const normalizePriority = (value: unknown): Priority => {
  if (value === Priority.P0) return Priority.P0;
  if (value === Priority.P1) return Priority.P1;
  if (value === Priority.P2) return Priority.P2;
  return Priority.P1;
};

const normalizeOptionalPriority = (value: unknown): Priority | undefined => {
  if (value === Priority.P0) return Priority.P0;
  if (value === Priority.P1) return Priority.P1;
  if (value === Priority.P2) return Priority.P2;
  return undefined;
};

const normalizeRequirementStatus = (value: unknown): RequirementStatus => {
  if ((Object.values(RequirementStatus) as unknown[]).includes(value)) {
    return value as RequirementStatus;
  }
  return RequirementStatus.DRAFT;
};

const normalizeTestCaseStatus = (value: unknown): TestCaseStatus => {
  if (value === TestCaseStatus.DRAFT) return TestCaseStatus.DRAFT;
  if (value === TestCaseStatus.ASSIGNED) return TestCaseStatus.ASSIGNED;
  if (value === TestCaseStatus.DEVELOPING) return TestCaseStatus.DEVELOPING;
  if (value === TestCaseStatus.PENDING_REVIEW) return TestCaseStatus.PENDING_REVIEW;
  if (value === TestCaseStatus.DONE) return TestCaseStatus.DONE;
  return TestCaseStatus.DRAFT;
};

const normalizeTestCaseCategory = (value: unknown): TestCaseCategory | undefined => {
  if ((Object.values(TestCaseCategory) as unknown[]).includes(value)) {
    return value as TestCaseCategory;
  }
  return undefined;
};

const normalizeRiskLevel = (value: unknown): RiskLevel | undefined => {
  if (value === RiskLevel.LOW) return RiskLevel.LOW;
  if (value === RiskLevel.MEDIUM) return RiskLevel.MEDIUM;
  if (value === RiskLevel.HIGH) return RiskLevel.HIGH;
  return undefined;
};

const normalizeVisibilityScope = (value: unknown): VisibilityScope | undefined => {
  if (value === VisibilityScope.TEAM) return VisibilityScope.TEAM;
  if (value === VisibilityScope.PROJECT) return VisibilityScope.PROJECT;
  if (value === VisibilityScope.GLOBAL) return VisibilityScope.GLOBAL;
  return undefined;
};

const normalizeConfidentiality = (value: unknown): Confidentiality | undefined => {
  if (value === Confidentiality.PUBLIC) return Confidentiality.PUBLIC;
  if (value === Confidentiality.INTERNAL) return Confidentiality.INTERNAL;
  if (value === Confidentiality.NDA) return Confidentiality.NDA;
  return undefined;
};

const normalizeAttachment = (item: unknown): Attachment => {
  const row = asObject(item);
  const type = String(row.type || 'other');
  const attachmentType = ['image', 'video', 'spec', 'log', 'other'].includes(type) ? type as Attachment['type'] : 'other';
  return {
    id: String(row.id || ''),
    name: String(row.name || ''),
    type: attachmentType,
    url: String(row.url || ''),
    size: String(row.size || ''),
    uploaded_at: String(row.uploaded_at || ''),
  };
};

const normalizeStep = (item: unknown, index: number): TestStep => {
  const row = asObject(item);
  return {
    step_id: String(row.step_id || `step-${index + 1}`),
    name: String(row.name || ''),
    action: String(row.action || ''),
    expected: String(row.expected || ''),
  };
};

const normalizeUser = (item: unknown): User => {
  const row = asObject(item);
  const statusRaw = String(row.status || 'ACTIVE').toUpperCase();
  return {
    user_id: String(row.user_id || ''),
    username: String(row.username || ''),
    email: String(row.email || ''),
    role_ids: toArray<string>(row.role_ids),
    status: statusRaw === 'INACTIVE' ? 'INACTIVE' : 'ACTIVE',
    created_at: String(row.created_at || ''),
  };
};

const normalizeRequirement = (item: unknown): TestRequirement => {
  const row = asObject(item);
  const normalizedKeyParameters = toArray<Record<string, unknown>>(row.key_parameters)
    .map(param => ({
      key: String(param.key || ''),
      value: String(param.value || ''),
    }));

  return {
    req_id: String(row.req_id || ''),
    title: String(row.title || ''),
    description: String(row.description || ''),
    technical_spec: String(row.technical_spec || ''),
    target_components: toArray<string>(row.target_components),
    firmware_version: String(row.firmware_version || ''),
    priority: normalizePriority(row.priority),
    key_parameters: normalizedKeyParameters,
    risk_points: String(row.risk_points || ''),
    tpm_owner_id: String(row.tpm_owner_id || ''),
    manual_dev_id: String(row.manual_dev_id || ''),
    auto_dev_id: String(row.auto_dev_id || ''),
    status: normalizeRequirementStatus(row.status),
    attachments: toArray<unknown>(row.attachments).map(normalizeAttachment),
    created_at: String(row.created_at || ''),
    updated_at: String(row.updated_at || ''),
  };
};

const normalizeTestCase = (item: unknown): TestCase => {
  const row = asObject(item);
  const env = asObject(row.required_env);
  const approvalHistory = toArray<Record<string, unknown>>(row.approval_history)
    .map(record => ({
      approver: String(record.approver || ''),
      timestamp: String(record.timestamp || ''),
      result: (String(record.result || 'commented').toLowerCase() as 'approved' | 'rejected' | 'commented'),
      comment: String(record.comment || ''),
    }));

  return {
    case_id: String(row.case_id || ''),
    ref_req_id: String(row.ref_req_id || ''),
    title: String(row.title || ''),
    test_category: normalizeTestCaseCategory(row.test_category),
    version: Number(row.version || 1),
    is_active: Boolean(row.is_active ?? true),
    change_log: String(row.change_log || ''),
    status: normalizeTestCaseStatus(row.status),
    owner_id: String(row.owner_id || ''),
    reviewer_id: String(row.reviewer_id || ''),
    auto_dev_id: String(row.auto_dev_id || ''),
    priority: normalizeOptionalPriority(row.priority),
    estimated_duration_sec: row.estimated_duration_sec === undefined || row.estimated_duration_sec === null
      ? undefined
      : Number(row.estimated_duration_sec),
    target_components: toArray<string>(row.target_components),
    required_env: {
      os: String(env.os || ''),
      firmware: String(env.firmware || ''),
      hardware: String(env.hardware || ''),
      dependencies: toArray<string>(env.dependencies),
    },
    tags: toArray<string>(row.tags),
    tooling_req: toArray<string>(row.tooling_req),
    pre_condition: String(row.pre_condition || ''),
    post_condition: String(row.post_condition || ''),
    cleanup_steps: toArray<unknown>(row.cleanup_steps).map(normalizeStep),
    steps: toArray<unknown>(row.steps).map(normalizeStep),
    is_need_auto: Boolean(row.is_need_auto ?? false),
    is_automated: Boolean(row.is_automated ?? false),
    is_destructive: Boolean(row.is_destructive ?? false),
    automation_type: String(row.automation_type || ''),
    script_entity_id: String(row.script_entity_id || ''),
    risk_level: normalizeRiskLevel(row.risk_level),
    visibility_scope: normalizeVisibilityScope(row.visibility_scope),
    confidentiality: normalizeConfidentiality(row.confidentiality),
    attachments: toArray<unknown>(row.attachments).map(normalizeAttachment),
    custom_fields: asObject(row.custom_fields) as Record<string, string>,
    failure_analysis: String(row.failure_analysis || ''),
    deprecation_reason: String(row.deprecation_reason || ''),
    approval_history: approvalHistory,
    created_at: String(row.created_at || ''),
    updated_at: String(row.updated_at || ''),
  };
};

const normalizeUsers = (input: unknown): User[] => {
  return extractList(input).map(normalizeUser);
};

const normalizeRequirements = (input: unknown): TestRequirement[] => {
  return extractList(input).map(normalizeRequirement);
};

const normalizeTestCases = (input: unknown): TestCase[] => {
  return extractList(input).map(normalizeTestCase);
};

export default function App() {
  // Auth state
  const [view, setView] = useState<View>('login');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isAuthRestored, setIsAuthRestored] = useState(!isBackendEnabled);
  const [myPermissionCodes, setMyPermissionCodes] = useState<string[]>([]);
  const [availableNavViews, setAvailableNavViews] = useState<NavView[]>(FALLBACK_NAV_VIEWS);
  const [userNavigationMap, setUserNavigationMap] = useState<Record<string, NavView[]>>({});
  const [editingNavigationUser, setEditingNavigationUser] = useState<User | null>(null);
  const [editingNavigationViews, setEditingNavigationViews] = useState<NavView[]>([]);
  const [isSavingNavigation, setIsSavingNavigation] = useState(false);

  // Login form state
  const [loginForm, setLoginForm] = useState({ user_id: '', password: '', rememberMe: false });
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');

  // User management state
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newUser, setNewUser] = useState<Partial<User>>({ status: 'ACTIVE', role_ids: [] });

  // User profile popup state
  const [showUserProfile, setShowUserProfile] = useState(false);

  // Requirements state
  const [requirements, setRequirements] = useState<TestRequirement[]>([]);
  const [selectedReq, setSelectedReq] = useState<TestRequirement | null>(null);

  // Test cases state
  const [testCases, setTestCases] = useState<TestCase[]>([]);

  const getEffectiveUserNavViews = useCallback((user: User): NavView[] => {
    const customViews = userNavigationMap[user.user_id];
    if (customViews && customViews.length > 0) {
      return sanitizeNavViews(customViews);
    }
    return getDefaultNavViewsForUser(user);
  }, [userNavigationMap]);

  const refreshMyNavigationAccess = useCallback(async (user: User) => {
    const fallbackViews = getEffectiveUserNavViews(user);
    const fallbackPermissions = hasAdminRole(user)
      ? ['all']
      : fallbackViews.map(view => NAV_VIEW_PERMISSION_MAP[view]);

    setMyPermissionCodes(fallbackPermissions);
    setAvailableNavViews(fallbackViews);

    if (!isBackendEnabled || !testDesignerApi) {
      return fallbackViews;
    }

    const [permissionsResult, navigationResult] = await Promise.allSettled([
      testDesignerApi.getMyPermissions(),
      testDesignerApi.getMyNavigation(),
    ]);

    let normalizedPermissions = fallbackPermissions;
    if (permissionsResult.status === 'fulfilled') {
      const payload = unwrapApiData(permissionsResult.value);
      const parsed = normalizePermissionCodes(payload);
      if (parsed.length > 0) {
        normalizedPermissions = parsed;
      }
    } else {
      console.warn('Failed to load current user permissions, fallback to role-based defaults:', permissionsResult.reason);
    }

    let resolvedViews = fallbackViews;
    if (navigationResult.status === 'fulfilled') {
      const payload = unwrapApiData(navigationResult.value);
      const parsed = normalizeNavigationViews(payload);
      if (parsed.length > 0) {
        resolvedViews = parsed;
      } else {
        const derived = deriveNavViewsFromPermissions(normalizedPermissions);
        if (derived.length > 0) {
          resolvedViews = derived;
        }
      }
    } else {
      console.warn('Failed to load current user navigation access, fallback to permissions/defaults:', navigationResult.reason);
      const derived = deriveNavViewsFromPermissions(normalizedPermissions);
      if (derived.length > 0) {
        resolvedViews = derived;
      }
    }

    const safeViews = resolvedViews.length > 0 ? resolvedViews : FALLBACK_NAV_VIEWS;
    if (hasAdminRole(user)) {
      const allViews = NAVIGATION_OPTIONS.map(item => item.view);
      setMyPermissionCodes(['all']);
      setAvailableNavViews(allViews);
      return allViews;
    }
    setMyPermissionCodes(normalizedPermissions);
    setAvailableNavViews(safeViews);
    return safeViews;
  }, [getEffectiveUserNavViews]);

  // 先恢复登录状态（token + user），再触发后续受保护接口请求
  useEffect(() => {
    if (!isBackendEnabled) {
      setIsAuthRestored(true);
      return;
    }

    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    const userStr = localStorage.getItem('user_info') || sessionStorage.getItem('user_info');

    if (!token || !userStr) {
      setAccessTokenState(null);
      clearAccessToken();
      setMyPermissionCodes([]);
      setAvailableNavViews(FALLBACK_NAV_VIEWS);
      setIsAuthRestored(true);
      return;
    }

    try {
      const user = JSON.parse(userStr) as User;
      setAccessTokenState(token);
      setAccessToken(token);
      setCurrentUser(user);
      setIsLoggedIn(true);
      const defaultViews = getDefaultNavViewsForUser(user);
      setAvailableNavViews(defaultViews);
      setMyPermissionCodes(hasAdminRole(user) ? ['all'] : defaultViews.map(item => NAV_VIEW_PERMISSION_MAP[item]));
      setView(defaultViews[0] || 'req_list');
    } catch (error) {
      console.error('Failed to restore login state:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('user_info');
      setAccessTokenState(null);
      clearAccessToken();
      setMyPermissionCodes([]);
      setAvailableNavViews(FALLBACK_NAV_VIEWS);
    } finally {
      setIsAuthRestored(true);
    }
  }, []);

  // token 就绪后再拉取受保护资源
  useEffect(() => {
    if (!isBackendEnabled || !testDesignerApi) {
      return;
    }
    if (!isAuthRestored || !isLoggedIn || !accessToken || !currentUser) {
      return;
    }

    let isMounted = true;

    const loadInitialData = async () => {
      const [usersResult, requirementsResult, testCasesResult] = await Promise.allSettled([
        testDesignerApi.listUsers(),
        testDesignerApi.listRequirements(),
        testDesignerApi.listTestCases(),
      ]);
      await refreshMyNavigationAccess(currentUser);

      if (!isMounted) {
        return;
      }

      if (usersResult.status === 'fulfilled') {
        const usersPayload = unwrapApiData(usersResult.value);
        setUsers(normalizeUsers(usersPayload));
      } else {
        console.warn('Failed to load users from backend (possible non-admin account):', usersResult.reason);
      }

      if (requirementsResult.status === 'fulfilled') {
        const requirementsPayload = unwrapApiData(requirementsResult.value);
        setRequirements(normalizeRequirements(requirementsPayload));
      } else {
        console.error('Failed to load requirements from backend:', requirementsResult.reason);
      }

      if (testCasesResult.status === 'fulfilled') {
        const testCasesPayload = unwrapApiData(testCasesResult.value);
        setTestCases(normalizeTestCases(testCasesPayload));
      } else {
        console.error('Failed to load test cases from backend:', testCasesResult.reason);
      }
    };

    void loadInitialData();

    return () => {
      isMounted = false;
    };
  }, [isAuthRestored, isLoggedIn, accessToken, currentUser, refreshMyNavigationAccess]);

  // Form data for test case
  const [formData, setFormData] = useState<TestCase>({
    case_id: 'TC-SRV-2024-001',
    ref_req_id: '',
    title: '',
    test_category: TestCaseCategory.STRESS,
    version: 1,
    is_active: true,
    change_log: '初始版本创建。',
    status: TestCaseStatus.DRAFT,
    owner_id: 'eng_zhang_san',
    reviewer_id: 'lead_li_si',
    auto_dev_id: '',
    priority: Priority.P0,
    estimated_duration_sec: 3600,
    target_components: [],
    required_env: { os: 'Redhat', firmware: '', hardware: '', dependencies: [] },
    tags: [],
    tooling_req: [],
    pre_condition: '',
    post_condition: '',
    cleanup_steps: [],
    steps: [],
    is_need_auto: true,
    is_automated: false,
    is_destructive: false,
    automation_type: '',
    script_entity_id: '',
    risk_level: RiskLevel.MEDIUM,
    visibility_scope: VisibilityScope.PROJECT,
    confidentiality: Confidentiality.INTERNAL,
    attachments: [],
    custom_fields: {},
    failure_analysis: '',
    approval_history: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  });

  // Form data for requirement
  const [reqFormData, setReqFormData] = useState<TestRequirement>({
    req_id: `TR-${new Date().getFullYear()}-${String(requirements.length + 1).padStart(3, '0')}`,
    title: '',
    description: '',
    technical_spec: '',
    target_components: [],
    firmware_version: '',
    priority: Priority.P1,
    key_parameters: [],
    risk_points: '',
    tpm_owner_id: 'current_user',
    manual_dev_id: '',
    auto_dev_id: '',
    status: RequirementStatus.DRAFT,
    attachments: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  });

  // UI state
  const [activeSection, setActiveSection] = useState('basic');
  const [reqActiveSection, setReqActiveSection] = useState('basic');
  const [isPolishing, setIsPolishing] = useState<{ [key: string]: boolean }>({});
  const [isGeneratingSteps, setIsGeneratingSteps] = useState(false);

  // AI hook
  const { polishText: aiPolishText, generateSteps: aiGenerateSteps } = useLocalAI();

  const getLandingNavView = useCallback((views: NavView[]): NavView => {
    const safeViews = views.length > 0 ? views : FALLBACK_NAV_VIEWS;
    if (safeViews.includes('req_list')) {
      return 'req_list';
    }
    return safeViews[0];
  }, []);

  // Close user profile when changing views
  const handleViewChange = useCallback((viewName: View) => {
    setShowUserProfile(false);
    if (isNavView(viewName) && !availableNavViews.includes(viewName)) {
      const fallback = getLandingNavView(availableNavViews);
      if (fallback !== viewName) {
        alert('当前账号无权访问该页面');
      }
      setView(fallback);
      return;
    }
    setView(viewName);
  }, [availableNavViews, getLandingNavView]);

  // Login handlers
  const handleLogin = useCallback(async () => {
    if (!loginForm.user_id || !loginForm.password) {
      setLoginError('请输入用户ID和密码');
      return;
    }

    // 尝试使用后端登录
    if (isBackendEnabled && testDesignerApi) {
      try {
        const response = await testDesignerApi.login(loginForm.user_id, loginForm.password);
        const loginResult = unwrapApiData(response);

        if (!loginResult?.access_token || !loginResult.user) {
          throw new Error('Invalid login response');
        }

        const { access_token, user } = loginResult;
        const defaultViews = getDefaultNavViewsForUser(user);

        // 存储令牌和用户信息
        setAccessTokenState(access_token);
        setAccessToken(access_token);
        setCurrentUser(user);
        setIsLoggedIn(true);
        setAvailableNavViews(defaultViews);
        setMyPermissionCodes(hasAdminRole(user) ? ['all'] : defaultViews.map(view => NAV_VIEW_PERMISSION_MAP[view]));
        setLoginError('');

        // 根据 rememberMe 决定存储位置
        if (loginForm.rememberMe) {
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('user_info', JSON.stringify(user));
        } else {
          sessionStorage.setItem('access_token', access_token);
          sessionStorage.setItem('user_info', JSON.stringify(user));
        }

        const resolvedViews = await refreshMyNavigationAccess(user);
        setView(getLandingNavView(resolvedViews));
        return;
      } catch (error: any) {
        console.error('Login failed:', error);
        setLoginError(error?.message || '登录失败，请检查用户名和密码');
        return;
      }
    }

    // 降级到本地模拟数据（开发/演示模式）
    const user = users.find(u => u.user_id === loginForm.user_id && u.status === 'ACTIVE');
    if (user) {
      setCurrentUser(user);
      setIsLoggedIn(true);
      setLoginError('');
      const resolvedViews = await refreshMyNavigationAccess(user);
      setView(getLandingNavView(resolvedViews));
    } else {
      setLoginError('用户ID或密码错误');
    }
  }, [loginForm.user_id, loginForm.password, loginForm.rememberMe, users, refreshMyNavigationAccess, getLandingNavView]);

  const handleLogout = useCallback(() => {
    setIsLoggedIn(false);
    setCurrentUser(null);
    setAccessTokenState(null);
    setMyPermissionCodes([]);
    setAvailableNavViews(FALLBACK_NAV_VIEWS);
    setEditingNavigationUser(null);
    setEditingNavigationViews([]);
    setUserNavigationMap({});
    setAccessToken(null);
    clearAccessToken();

    // 清除存储的令牌
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('user_info');

    setShowUserProfile(false);
    setView('login');
  }, []);

  const handleQuickLogin = useCallback((user_id: string, password: string) => {
    setLoginForm({ user_id, password, rememberMe: false });
    setLoginError('');
    // 延迟一点时间让表单更新，然后执行登录
    setTimeout(async () => {
      await handleLogin();
    }, 50);
  }, [handleLogin]);

  useEffect(() => {
    if (!isLoggedIn) {
      return;
    }
    if (isNavView(view) && !availableNavViews.includes(view)) {
      setView(getLandingNavView(availableNavViews));
    }
  }, [isLoggedIn, view, availableNavViews, getLandingNavView]);

  // Requirement form handlers
  const updateReqField = useCallback((field: keyof TestRequirement, value: any) => {
    setReqFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const toggleReqComponent = useCallback((comp: string) => {
    setReqFormData(prev => {
      const current = prev.target_components;
      if (current.includes(comp)) {
        return { ...prev, target_components: current.filter(c => c !== comp) };
      } else {
        return { ...prev, target_components: [...current, comp] };
      }
    });
  }, []);

  const polishText = useCallback(async (field: 'description' | 'technical_spec') => {
    const text = reqFormData[field];
    if (!text) return;

    setIsPolishing(prev => ({ ...prev, [field]: true }));
    try {
      await aiPolishText(text, field, (resultField, result) => {
        updateReqField(resultField, result);
      });
    } finally {
      setIsPolishing(prev => ({ ...prev, [field]: false }));
    }
  }, [reqFormData.description, reqFormData.technical_spec, aiPolishText, updateReqField]);

  const addReqAttachment = useCallback(() => {
    const newAttachment: Attachment = {
      id: `att-${Date.now()}`,
      name: '需求规范文档.pdf',
      type: 'spec',
      url: '#',
      size: '2.5 MB',
      uploaded_at: new Date().toISOString()
    };
    setReqFormData(prev => ({ ...prev, attachments: [...prev.attachments, newAttachment] }));
  }, []);

  const removeReqAttachment = useCallback((id: string) => {
    setReqFormData(prev => ({ ...prev, attachments: prev.attachments.filter(a => a.id !== id) }));
  }, []);

  const saveRequirement = useCallback(async () => {
    const createPayload: CreateRequirementPayload = {
      req_id: reqFormData.req_id,
      title: reqFormData.title,
      description: reqFormData.description,
      technical_spec: reqFormData.technical_spec,
      target_components: reqFormData.target_components,
      firmware_version: reqFormData.firmware_version,
      priority: reqFormData.priority,
      key_parameters: reqFormData.key_parameters,
      risk_points: reqFormData.risk_points,
      tpm_owner_id: reqFormData.tpm_owner_id,
      manual_dev_id: reqFormData.manual_dev_id,
      auto_dev_id: reqFormData.auto_dev_id,
      attachments: reqFormData.attachments,
    };

    if (isBackendEnabled && testDesignerApi) {
      try {
        const response = await testDesignerApi.createRequirement(createPayload);
        const savedRequirement = unwrapApiData(response);
        if (!savedRequirement) {
          throw new Error('Invalid create requirement response');
        }
        setRequirements(prev => [...prev, savedRequirement]);
      } catch (error) {
        console.error('Failed to save requirement to backend:', error);
        alert('需求保存失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setRequirements(prev => [
        ...prev,
        {
          ...createPayload,
          status: RequirementStatus.DRAFT,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    }

    handleViewChange('req_list');
    // Reset form
    setReqFormData({
      req_id: `TR-${new Date().getFullYear()}-${String(requirements.length + 2).padStart(3, '0')}`,
      title: '',
      description: '',
      technical_spec: '',
      target_components: [],
      firmware_version: '',
      priority: Priority.P1,
      key_parameters: [],
      risk_points: '',
      tpm_owner_id: 'current_user',
      manual_dev_id: '',
      auto_dev_id: '',
      status: RequirementStatus.DRAFT,
      attachments: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }, [reqFormData, requirements.length, handleViewChange]);

  // Case form handlers
  const updateField = useCallback((path: string, value: any) => {
    setFormData(prev => {
      const newData = { ...prev };
      if (path.includes('.')) {
        const [parent, child] = path.split('.');
        (newData as any)[parent] = { ...(newData as any)[parent], [child]: value };
      } else {
        (newData as any)[path] = value;
      }
      return newData;
    });
  }, []);

  const addStep = useCallback(() => {
    const newStep: TestStep = {
      step_id: (formData.steps.length + 1).toString(),
      name: '',
      action: '',
      expected: ''
    };
    setFormData(prev => ({ ...prev, steps: [...prev.steps, newStep] }));
  }, [formData.steps.length]);

  const removeStep = useCallback((id: string) => {
    setFormData(prev => ({ ...prev, steps: prev.steps.filter(s => s.step_id !== id) }));
  }, []);

  const updateStep = useCallback((id: string, field: keyof TestStep, value: string) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.map(s => s.step_id === id ? { ...s, [field]: value } : s)
    }));
  }, []);

  const addAttachment = useCallback(() => {
    const newAttachment: Attachment = {
      id: `att-${Date.now()}`,
      name: '新附件.pdf',
      type: 'spec',
      url: '#',
      size: '1.2 MB',
      uploaded_at: new Date().toISOString()
    };
    setFormData(prev => ({ ...prev, attachments: [...prev.attachments, newAttachment] }));
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setFormData(prev => ({ ...prev, attachments: prev.attachments.filter(a => a.id !== id) }));
  }, []);

  const generateStepsWithAI = useCallback(async () => {
    const linkedReq = requirements.find(r => r.req_id === formData.ref_req_id);
    if (!linkedReq) {
      alert("请先关联有效的测试需求 ID");
      return;
    }

    setIsGeneratingSteps(true);
    try {
      await aiGenerateSteps(
        linkedReq.title,
        linkedReq.description,
        linkedReq.technical_spec,
        linkedReq.key_parameters,
        (steps) => {
          setFormData(prev => ({ ...prev, steps }));
        }
      );
    } finally {
      setIsGeneratingSteps(false);
    }
  }, [requirements, formData.ref_req_id, aiGenerateSteps]);

  const saveTestCase = useCallback(async () => {
    const nextCaseId = `TC-${Date.now()}`;
    const createPayload: CreateTestCasePayload = {
      case_id: nextCaseId,
      ref_req_id: formData.ref_req_id,
      title: formData.title,
      test_category: formData.test_category,
      version: formData.version,
      is_active: formData.is_active,
      change_log: formData.change_log,
      owner_id: formData.owner_id,
      reviewer_id: formData.reviewer_id,
      auto_dev_id: formData.auto_dev_id,
      priority: formData.priority,
      estimated_duration_sec: formData.estimated_duration_sec,
      target_components: formData.target_components,
      required_env: formData.required_env,
      tags: formData.tags,
      tooling_req: formData.tooling_req,
      pre_condition: formData.pre_condition,
      post_condition: formData.post_condition,
      cleanup_steps: formData.cleanup_steps,
      steps: formData.steps,
      is_need_auto: formData.is_need_auto,
      is_automated: formData.is_automated,
      is_destructive: formData.is_destructive,
      automation_type: formData.automation_type,
      script_entity_id: formData.script_entity_id,
      risk_level: formData.risk_level,
      visibility_scope: formData.visibility_scope,
      confidentiality: formData.confidentiality,
      attachments: formData.attachments,
      custom_fields: formData.custom_fields,
      failure_analysis: formData.failure_analysis,
      deprecation_reason: formData.deprecation_reason,
      approval_history: formData.approval_history,
    };

    if (isBackendEnabled && testDesignerApi) {
      try {
        const response = await testDesignerApi.createTestCase(createPayload);
        const savedTestCase = unwrapApiData(response);
        if (!savedTestCase) {
          throw new Error('Invalid create test case response');
        }
        setTestCases(prev => [...prev, savedTestCase]);
      } catch (error) {
        console.error('Failed to save test case to backend:', error);
        alert('用例保存失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setTestCases(prev => [
        ...prev,
        {
          ...createPayload,
          status: TestCaseStatus.DRAFT,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    }

    handleViewChange('req_detail');
  }, [formData, handleViewChange]);

  // User management handlers
  const handleCreateUser = useCallback(async () => {
    if (!newUser.username || !newUser.email) return;
    const userToCreate: User = {
      user_id: `u-${Math.floor(Math.random() * 10000)}`,
      username: newUser.username,
      email: newUser.email,
      role_ids: newUser.role_ids || [],
      status: 'ACTIVE',
      created_at: new Date().toISOString().split('T')[0]
    };
    let finalUser = userToCreate;

    if (isBackendEnabled && testDesignerApi) {
      try {
        const createdUser = await testDesignerApi.createUser(userToCreate);
        finalUser = createdUser;
        setUsers(prev => [...prev, createdUser]);
      } catch (error) {
        console.error('Failed to create user in backend:', error);
        alert('用户创建失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setUsers(prev => [...prev, userToCreate]);
    }
    setUserNavigationMap(prev => ({ ...prev, [finalUser.user_id]: getDefaultNavViewsForUser(finalUser) }));

    setShowUserForm(false);
    setNewUser({ status: 'ACTIVE', role_ids: [] });
    console.log('Created User Request Example:', JSON.stringify(userToCreate, null, 2));
  }, [newUser]);

  const startEditUser = useCallback((user: User) => {
    setEditingUser({ ...user });
  }, []);

  const saveEditUser = useCallback(async (updatedUser: User) => {
    if (isBackendEnabled && testDesignerApi) {
      try {
        await testDesignerApi.updateUser(updatedUser.user_id, updatedUser);
      } catch (error) {
        console.error('Failed to update user in backend:', error);
        alert('用户更新失败，请检查后端服务后重试。');
        return;
      }
    }

    setUsers(prev => prev.map(u => u.user_id === updatedUser.user_id ? updatedUser : u));
    setEditingUser(null);
  }, []);

  const cancelEditUser = useCallback(() => {
    setEditingUser(null);
  }, []);

  const handleEditFieldChange = useCallback((field: string, value: any) => {
    setEditingUser(prev => {
      if (!prev) return null;
      return { ...prev, [field]: value };
    });
  }, []);

  const startEditNavigation = useCallback(async (user: User) => {
    if (!hasAdminRole(currentUser)) {
      alert('仅管理员可配置导航权限');
      return;
    }

    const fallbackViews = getEffectiveUserNavViews(user);
    setEditingNavigationUser(user);
    setEditingNavigationViews(fallbackViews);

    if (!isBackendEnabled || !testDesignerApi) {
      return;
    }

    try {
      const remoteNavigation = await testDesignerApi.getUserNavigation(user.user_id);
      const navigationPayload = unwrapApiData(remoteNavigation);
      const parsedViews = normalizeNavigationViews(navigationPayload);
      if (parsedViews.length > 0) {
        setEditingNavigationViews(parsedViews);
      }
    } catch (error) {
      console.warn(`Failed to load navigation access for user ${user.user_id}, fallback to defaults/local cache:`, error);
    }
  }, [currentUser, getEffectiveUserNavViews]);

  const toggleEditingNavigationView = useCallback((targetView: string) => {
    if (!isNavView(targetView)) {
      return;
    }
    setEditingNavigationViews(prev => {
      if (prev.includes(targetView)) {
        return prev.filter(viewItem => viewItem !== targetView);
      }
      return sanitizeNavViews([...prev, targetView]);
    });
  }, []);

  const cancelEditNavigation = useCallback(() => {
    setEditingNavigationUser(null);
    setEditingNavigationViews([]);
    setIsSavingNavigation(false);
  }, []);

  const saveEditNavigation = useCallback(async () => {
    if (!editingNavigationUser) {
      return;
    }

    const normalizedViews = sanitizeNavViews(editingNavigationViews);
    if (normalizedViews.length === 0) {
      alert('至少保留一个可访问页面');
      return;
    }

    setIsSavingNavigation(true);
    try {
      if (isBackendEnabled && testDesignerApi) {
        await testDesignerApi.updateUserNavigation(editingNavigationUser.user_id, normalizedViews);
      }

      setUserNavigationMap(prev => ({ ...prev, [editingNavigationUser.user_id]: normalizedViews }));

      if (currentUser?.user_id === editingNavigationUser.user_id) {
        if (hasAdminRole(currentUser)) {
          const allViews = NAVIGATION_OPTIONS.map(item => item.view);
          setAvailableNavViews(allViews);
          setMyPermissionCodes(['all']);
        } else {
          setAvailableNavViews(normalizedViews);
          setMyPermissionCodes(normalizedViews.map(view => NAV_VIEW_PERMISSION_MAP[view]));
        }
      }

      setEditingNavigationUser(null);
      setEditingNavigationViews([]);
    } catch (error) {
      console.error(`Failed to save navigation access for user ${editingNavigationUser.user_id}:`, error);
      alert('导航权限保存失败，请检查后端服务后重试。');
    } finally {
      setIsSavingNavigation(false);
    }
  }, [editingNavigationUser, editingNavigationViews, currentUser]);

  // Render views based on current view
  if (view === 'login' || !isLoggedIn) {
    return (
      <Login
        loginForm={loginForm}
        showPassword={showPassword}
        loginError={loginError}
        onLoginFormChange={setLoginForm}
        onShowPasswordChange={setShowPassword}
        onLogin={handleLogin}
        onQuickLogin={handleQuickLogin}
      />
    );
  }

  if (view === 'user_mgmt') {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex">
        {/* Left Sidebar - Navigation */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
          {/* Logo */}
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg shadow-slate-900/20">
                <FileText size={22} className="text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-slate-900">Test Designer</h1>
                <p className="text-[10px] text-slate-400">服务器测试平台</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {availableNavViews.includes('req_list') && (
              <button
                onClick={() => handleViewChange('req_list')}
                className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
              >
                <FileText size={18} />
                测试需求
              </button>
            )}
            {availableNavViews.includes('case_list') && (
              <button
                onClick={() => handleViewChange('case_list')}
                className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
              >
                <PlayCircle size={18} />
                测试用例
              </button>
            )}
            <button
              onClick={() => {}}
              className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20"
            >
              <UserIcon size={18} />
              用户管理
            </button>
          </nav>

          {/* Bottom User Info */}
          <div className="p-4 border-t border-slate-100">
            {currentUser && (
              <>
                <button
                  onClick={() => setShowUserProfile(true)}
                  className="w-full flex items-center gap-3 p-3 bg-slate-50 rounded-xl mb-3 hover:bg-slate-100 transition-colors cursor-pointer group"
                >
                  <div className="w-9 h-9 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                    <UserIcon size={16} className="text-indigo-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-700 truncate">{currentUser.username}</div>
                    <div className="text-[10px] text-slate-400">{currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}</div>
                  </div>
                </button>

                {/* User Profile Popup */}
                {showUserProfile && (
                  <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div
                      className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
                      onClick={() => setShowUserProfile(false)}
                    />
                    <div className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden">
                      {/* Header */}
                      <div className="px-6 py-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
                        <div className="flex items-center justify-between">
                          <h2 className="text-lg font-bold">个人信息</h2>
                          <button
                            onClick={() => setShowUserProfile(false)}
                            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
                          >
                            <X size={20} />
                          </button>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="p-6 space-y-5">
                        {/* Avatar and Name */}
                        <div className="flex items-center gap-4">
                          <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center">
                            <UserIcon size={32} className="text-indigo-600" />
                          </div>
                          <div>
                            <div className="text-xl font-bold text-slate-900">{currentUser.username}</div>
                            <div className="text-sm text-slate-500">
                              {currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}
                            </div>
                            <span className={`inline-flex items-center mt-2 px-2 py-0.5 rounded-lg text-xs font-bold ${
                              currentUser.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'
                            }`}>
                              {currentUser.status === 'ACTIVE' ? '已启用' : '已禁用'}
                            </span>
                          </div>
                        </div>

                        {/* Details */}
                        <div className="space-y-3 pt-4 border-t border-slate-100">
                          <div className="flex items-center gap-3 text-sm">
                            <Mail size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">邮箱地址</div>
                              <div className="font-medium text-slate-700">{currentUser.email}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <Shield size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">用户角色</div>
                              <div className="flex gap-1.5 mt-1">
                                {currentUser.role_ids.map(rid => (
                                  <span key={rid} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-bold">
                                    {ROLES.find(r => r.id === rid)?.name || rid}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <Calendar size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">创建时间</div>
                              <div className="font-medium text-slate-700">{currentUser.created_at}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <div className="w-4 h-4 flex items-center justify-center">
                              <div className="w-2 h-2 bg-slate-400 rounded-full" />
                            </div>
                            <div>
                              <div className="text-xs text-slate-400">用户 ID</div>
                              <div className="font-mono text-xs text-slate-600">{currentUser.user_id}</div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Footer */}
                      <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex gap-3">
                        <button
                          onClick={() => setShowUserProfile(false)}
                          className="flex-1 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                        >
                          关闭
                        </button>
                        <button
                          onClick={() => {
                            setShowUserProfile(false);
                            handleViewChange('user_mgmt');
                          }}
                          className="flex-1 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all"
                        >
                          编辑资料
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl text-sm font-bold transition-colors"
            >
              <LogIn size={16} className="rotate-180" />
              退出登录
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="max-w-full h-full">
            <UserMgmt
              users={users}
              currentUser={currentUser}
              showUserForm={showUserForm}
              editingUser={editingUser}
              editingNavigationUser={editingNavigationUser}
              editingNavigationViews={editingNavigationViews}
              isSavingNavigation={isSavingNavigation}
              navigationOptions={NAVIGATION_OPTIONS}
              newUser={newUser}
              onBack={() => handleViewChange(getLandingNavView(availableNavViews))}
              onShowUserForm={setShowUserForm}
              onNewUserChange={setNewUser}
              onCreateUser={handleCreateUser}
              onStartEditUser={startEditUser}
              onSaveEditUser={saveEditUser}
              onCancelEdit={cancelEditUser}
              onEditFieldChange={handleEditFieldChange}
              onStartEditNavigation={startEditNavigation}
              onToggleEditNavigationView={toggleEditingNavigationView}
              onSaveEditNavigation={saveEditNavigation}
              onCancelEditNavigation={cancelEditNavigation}
            />
          </div>
        </main>
      </div>
    );
  }

  if (view === 'req_form') {
    return (
      <ReqForm
        formData={reqFormData}
        activeSection={reqActiveSection}
        isPolishing={isPolishing}
        onFieldChange={updateReqField}
        onSave={saveRequirement}
        onCancel={() => handleViewChange('req_list')}
        onAddAttachment={addReqAttachment}
        onRemoveAttachment={removeReqAttachment}
        onToggleComponent={toggleReqComponent}
        onPolishText={polishText}
        onSectionChange={setReqActiveSection}
      />
    );
  }

  if (view === 'req_detail' && selectedReq) {
    return (
      <ReqDetail
        requirement={selectedReq}
        testCases={testCases}
        onBack={() => handleViewChange('req_list')}
        onCreateCase={(refReqId) => {
          setFormData(prev => ({ ...prev, ref_req_id: refReqId }));
          handleViewChange('case_form');
        }}
        onSelectCase={(tc) => {
          setFormData(tc);
          handleViewChange('case_form');
        }}
      />
    );
  }

  if (view === 'case_form') {
    return (
      <CaseForm
        formData={formData}
        activeSection={activeSection}
        isGeneratingSteps={isGeneratingSteps}
        onFieldChange={updateField}
        onAddStep={addStep}
        onRemoveStep={removeStep}
        onUpdateStep={updateStep}
        onAddAttachment={addAttachment}
        onRemoveAttachment={removeAttachment}
        onSave={saveTestCase}
        onCancel={() => setView('req_detail')}
        onGenerateSteps={generateStepsWithAI}
        onSectionChange={setActiveSection}
      />
    );
  }

  if (view === 'case_list') {
    return (
      <CaseList
        testCases={testCases}
        currentUser={currentUser}
        availableNavViews={availableNavViews}
        onSelectCase={(tc) => {
          setFormData(tc);
          handleViewChange('case_form');
        }}
        onCreateCase={() => {
          setFormData({
            case_id: 'TC-SRV-2024-001',
            ref_req_id: '',
            title: '',
            test_category: TestCaseCategory.STRESS,
            version: 1,
            is_active: true,
            change_log: '初始版本创建。',
            status: TestCaseStatus.DRAFT,
            owner_id: currentUser?.user_id || '',
            reviewer_id: '',
            auto_dev_id: '',
            priority: Priority.P0,
            estimated_duration_sec: 3600,
            target_components: [],
            required_env: { os: '', firmware: '', hardware: '', dependencies: [] },
            tags: [],
            tooling_req: [],
            pre_condition: '',
            post_condition: '',
            cleanup_steps: [],
            steps: [],
            is_need_auto: false,
            is_automated: false,
            is_destructive: false,
            automation_type: '',
            script_entity_id: '',
            risk_level: RiskLevel.MEDIUM,
            visibility_scope: VisibilityScope.PROJECT,
            confidentiality: Confidentiality.INTERNAL,
            attachments: [],
            custom_fields: {},
            failure_analysis: '',
            approval_history: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          });
          handleViewChange('case_form');
        }}
        onNavigateToReqList={() => handleViewChange('req_list')}
        onNavigateToUserMgmt={() => handleViewChange('user_mgmt')}
        onLogout={handleLogout}
        showUserProfile={showUserProfile}
        onToggleUserProfile={() => setShowUserProfile(!showUserProfile)}
      />
    );
  }

  // Default: req_list view
  return (
    <ReqList
      requirements={requirements}
      currentUser={currentUser}
      availableNavViews={availableNavViews}
      onSelectReq={(req) => {
        setSelectedReq(req);
        handleViewChange('req_detail');
      }}
      onCreateReq={() => handleViewChange('req_form')}
      onNavigateToCaseList={() => handleViewChange('case_list')}
      onNavigateToUserMgmt={() => handleViewChange('user_mgmt')}
      onLogout={handleLogout}
      showUserProfile={showUserProfile}
      onToggleUserProfile={() => setShowUserProfile(!showUserProfile)}
    />
  );
}
