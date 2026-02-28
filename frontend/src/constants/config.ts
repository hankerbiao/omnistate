// User roles configuration
export interface Role {
  id: string;
  name: string;
  permissions: string[];
  description: string;
}

export interface User {
  user_id: string;
  username: string;
  email: string;
  role_ids: string[];
  status: 'ACTIVE' | 'INACTIVE';
  created_at: string;
}

export const ROLES: Role[] = [
  { id: 'ROLE_ADMIN', name: '管理员', permissions: ['all'], description: '系统最高权限' },
  { id: 'ROLE_TESTER', name: '测试工程师', permissions: ['case:read', 'case:write', 'req:read'], description: '负责用例编写与执行' },
  { id: 'ROLE_TPM', name: '测试经理', permissions: ['req:write', 'approval:write'], description: '负责需求定义与评审' },
];

export const INITIAL_USERS: User[] = [
  { user_id: 'u-1001', username: 'alice', email: 'alice@example.com', role_ids: ['ROLE_TESTER', 'ROLE_TPM'], status: 'ACTIVE', created_at: '2024-01-01' },
  { user_id: 'u-1002', username: 'bob', email: 'bob@example.com', role_ids: ['ROLE_TPM'], status: 'ACTIVE', created_at: '2024-01-05' },
  { user_id: 'u-1003', username: 'admin', email: 'admin@example.com', role_ids: ['ROLE_ADMIN', 'ROLE_TPM', 'ROLE_TESTER'], status: 'ACTIVE', created_at: '2024-01-01' },
];

// Backend API configuration
const timeoutMs = Number(import.meta.env.VITE_API_TIMEOUT_MS);
export const BACKEND_API_BASE_URL = import.meta.env.VITE_BACKEND_API_BASE_URL || '';
export const BACKEND_API_TIMEOUT_MS = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 15000;

// Local AI API configuration
export const LOCAL_AI_BASE_URL = 'http://172.17.167.43:8000/v1';
export const LOCAL_AI_MODEL = '/models/coder/minimax/MiniMax-M2';

// Component categories for test requirements
export const COMPONENT_CATEGORIES = ['Memory', 'NVMe_SSD', 'CPU', 'GPU', 'NIC', 'PSU', 'Fan'];

// Engineers list
export const ENGINEERS = ['eng_zhang_san', 'eng_li_si', 'eng_wang_wu', 'eng_zhao_liu'];
