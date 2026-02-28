/**
 * @fileoverview 配置常量文件
 * 定义系统角色、用户、API端点和业务常量
 */

// ========== 角色和用户配置 ==========

/**
 * 角色接口定义
 * 描述系统中的权限角色结构
 */
export interface Role {
  id: string;              // 角色唯一标识符
  name: string;            // 角色显示名称
  permissions: string[];   // 权限代码列表
  description: string;     // 角色描述说明
}

/**
 * 用户接口定义
 * 描述系统用户的完整信息
 */
export interface User {
  user_id: string;         // 用户唯一标识符
  username: string;        // 用户名
  email: string;           // 邮箱地址
  role_ids: string[];      // 关联的角色ID列表
  status: 'ACTIVE' | 'INACTIVE'; // 用户状态
  created_at: string;      // 创建时间戳
}

/**
 * 系统预定义角色配置
 * 定义了三种核心角色：管理员、测试工程师、测试经理
 */
export const ROLES: Role[] = [
  {
    id: 'ROLE_ADMIN',
    name: '管理员',
    permissions: ['all'],
    description: '系统最高权限 - 可访问所有功能模块'
  },
  {
    id: 'ROLE_TESTER',
    name: '测试工程师',
    permissions: ['case:read', 'case:write', 'req:read'],
    description: '负责测试用例编写与执行'
  },
  {
    id: 'ROLE_TPM',
    name: '测试经理',
    permissions: ['req:write', 'approval:write'],
    description: '负责需求定义与技术评审'
  },
];

/**
 * 初始用户数据
 * 系统预设的测试账户（开发环境使用）
 */
export const INITIAL_USERS: User[] = [
  {
    user_id: 'u-1001',
    username: 'alice',
    email: 'alice@example.com',
    role_ids: ['ROLE_TESTER', 'ROLE_TPM'],
    status: 'ACTIVE',
    created_at: '2024-01-01'
  },
  {
    user_id: 'u-1002',
    username: 'bob',
    email: 'bob@example.com',
    role_ids: ['ROLE_TPM'],
    status: 'ACTIVE',
    created_at: '2024-01-05'
  },
  {
    user_id: 'u-1003',
    username: 'admin',
    email: 'admin@example.com',
    role_ids: ['ROLE_ADMIN', 'ROLE_TPM', 'ROLE_TESTER'],
    status: 'ACTIVE',
    created_at: '2024-01-01'
  },
];

// ========== 后端API配置 ==========

/**
 * API请求超时时间（毫秒）
 * 从环境变量读取，默认为15秒
 */
const timeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS);

/**
 * 后端API基础URL
 * 从环境变量获取，支持开发和生产环境
 */
export const BACKEND_API_BASE_URL = import.meta.env.VITE_BACKEND_API_BASE_URL || '';

/**
 * API请求超时配置
 * 验证超时时间有效性，否则使用默认值
 */
export const BACKEND_API_TIMEOUT_MS = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 15000;

// ========== 本地AI服务配置 ==========

/**
 * 本地AI服务基础URL
 * 用于文本润色和测试步骤生成等AI辅助功能
 */
export const LOCAL_AI_BASE_URL = 'http://172.17.167.43:8000/v1';

/**
 * 本地AI服务模型路径
 * 使用MiniMax-M2模型（OpenAI兼容接口）
 */
export const LOCAL_AI_MODEL = '/models/coder/minimax/MiniMax-M2';

// ========== 业务常量配置 ==========

/**
 * 硬件组件类别列表
 * 测试需求中可选择的目标组件类型
 * 包括内存、存储、处理器、显卡等服务器硬件
 */
export const COMPONENT_CATEGORIES = [
  'Memory',    // 内存
  'NVMe_SSD',  // 固态硬盘
  'CPU',       // 中央处理器
  'GPU',       // 图形处理器
  'NIC',       // 网络接口卡
  'PSU',       // 电源供应器
  'Fan'        // 散热风扇
];

/**
 * 测试工程师列表
 * 系统中可指派的测试人员ID
 */
export const ENGINEERS = [
  'eng_zhang_san',
  'eng_li_si',
  'eng_wang_wu',
  'eng_zhao_liu'
];
