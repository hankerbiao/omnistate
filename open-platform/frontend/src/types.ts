// DML V4 开放平台 · 类型定义

export type UserRole = "admin" | "developer";

export interface MockUser {
  id: string;
  username: string | null;
  name: string;
  email: string;
  role: UserRole;
  team: string;
  avatar: string;
  allowedCapabilityIds: string[];
  /** 该用户的配额设置（普通用户生效，管理员不受约束） */
  quota: UserQuota;
  /** 首次登录或管理员重置后，必须先修改密码才能进入控制台 */
  mustChangePassword: boolean;
}

export interface LoginResponse {
  user: MockUser;
}

export interface CreateUserInput {
  username: string;
  role: UserRole;
  allowedCapabilityIds: string[];
  quota: UserQuota;
}

export interface ChangePasswordInput {
  oldPassword: string;
  newPassword: string;
}

/** 用户配额设置 */
export interface UserQuota {
  /** 是否启用配额限制；关闭后该用户不受调用上限约束 */
  enabled: boolean;
  /** 月度调用次数上限，0 表示不限制 */
  monthlyLimit: number;
  /** 每分钟请求数上限 (RPM)，0 表示不限制 */
  rpmLimit: number;
  /** 最大并发请求数，0 表示不限制 */
  concurrency: number;
}

export type ApiKeyStatus = "active" | "revoked";

export interface ApiKey {
  id: string;
  name: string;
  ownerUserId: string;
  /** 展示用前缀，如 dml_live_ */
  prefix: string;
  /** 掩码后的密钥，如 dml_live_a1b2••••••••7f9c */
  masked: string;
  status: ApiKeyStatus;
  scopes: string[];
  createdAt: string;
  lastUsedAt: string | null;
  /** 今日调用次数 */
  callsToday: number;
  /** 环境：生产 / 测试 */
  env: "live" | "test";
}

export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

export interface CapabilityParam {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface Capability {
  id: string;
  name: string;
  category: string;
  method: HttpMethod;
  path: string;
  summary: string;
  description: string;
  params: CapabilityParam[];
  scope: string;
  handler: "proxy" | "local" | "aggregate";
  upstreamPath: string | null;
  /** 示例响应（JSON 字符串） */
  sampleResponse: string;
}

export interface CurrentUserCapabilitiesResponse {
  user: MockUser;
  capabilities: Capability[];
}

export type LogStatus = "success" | "client_error" | "server_error";

export interface CallLog {
  id: string;
  timestamp: string;
  requestId: string;
  appName: string;
  keyName: string;
  method: HttpMethod;
  endpoint: string;
  statusCode: number;
  status: LogStatus;
  latencyMs: number;
  gatewayLatencyMs: number;
  ip: string;
  requestBody: string | null;
  responseBody: string;
  errorCode?: string;
  diagnosis?: string;
}

export interface OverviewStats {
  totalCallsToday: number;
  totalCallsTrend: number; // 相比昨日百分比
  successRate: number;
  successRateTrend: number;
  activeKeys: number;
  quotaUsed: number;
  quotaLimit: number;
  /** 近 7 日调用量 */
  daily: { date: string; calls: number; errors: number }[];
  /** 各能力调用占比 */
  topCapabilities: { name: string; calls: number }[];
}

/** 新建密钥的返回（含一次性明文） */
export interface CreatedApiKey {
  key: ApiKey;
  /** 仅创建时返回一次的明文密钥 */
  plaintext: string;
}

export interface DebugRequest {
  capabilityId: string;
  keyId: string;
  env: "live" | "test";
  params: Record<string, string>;
}

export interface DebugResponse {
  requestId: string;
  statusCode: number;
  latencyMs: number;
  requestUrl: string;
  responseBody: string;
}
