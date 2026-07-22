// DML V4 开放平台 · API 客户端。默认连接本地网关，显式开启时才使用 Mock。
import type {
  ApiKey,
  CallLog,
  ChangePasswordInput,
  Capability,
  CreateUserInput,
  CurrentUserCapabilitiesResponse,
  CreatedApiKey,
  DebugRequest,
  DebugResponse,
  LoginResponse,
  MockUser,
  OverviewStats,
  UserQuota,
} from "../types";
import type { MockArgs, MockOp } from "../mock/handlers";

// 构建期常量：生产构建未显式开启 VITE_OPEN_PLATFORM_USE_MOCK 时，下方 mock 分支
// 会被判定为死代码并由打包器剔除（见 vite.config.ts / vitest.config.ts）。
const USE_MOCK = __USE_MOCK__;
const gatewayBaseUrl = (
  import.meta.env.VITE_OPEN_PLATFORM_API_BASE_URL ?? "http://127.0.0.1:8820"
).replace(/\/$/, "");
const consoleToken = import.meta.env.VITE_OPEN_PLATFORM_CONSOLE_TOKEN ?? "dev-console-token";
let currentConsoleUserId = window.localStorage.getItem("dml-open-platform-user") ?? "user_admin";

function consoleHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-Console-Token": consoleToken,
    "X-Console-User-Id": currentConsoleUserId,
  };
}

async function gatewayRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${gatewayBaseUrl}/api/v1/open-platform${path}`, {
    ...init,
    headers: {
      ...consoleHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 0)
    throw new Error(payload.message || payload.detail || "开放平台网关请求失败");
  return payload.data as T;
}

async function withGateway<T>(
  path: string,
  op: MockOp,
  args: MockArgs,
  init?: RequestInit,
): Promise<T> {
  if (USE_MOCK) {
    const { runMock } = await import("../mock/handlers");
    return runMock<T>(op, args);
  }
  try {
    return await gatewayRequest<T>(path, init);
  } catch (error) {
    console.error("开放平台网关不可用，请确认 gateway_service 已启动", error);
    throw error;
  }
}

export const api = {
  setConsoleUserId(userId: string) {
    currentConsoleUserId = userId || "user_admin";
  },

  login(username: string, password: string): Promise<LoginResponse> {
    return withGateway<LoginResponse>(
      "/login",
      "login",
      { loginInput: { username, password } },
      { method: "POST", body: JSON.stringify({ username, password }) },
    );
  },

  getOverview(): Promise<OverviewStats> {
    return withGateway<OverviewStats>("/overview", "getOverview", {});
  },

  listUsers(): Promise<MockUser[]> {
    return withGateway<MockUser[]>("/users", "listUsers", {});
  },

  createUser(input: CreateUserInput): Promise<MockUser> {
    return withGateway<MockUser>(
      "/users",
      "createUser",
      { createUserInput: input },
      { method: "POST", body: JSON.stringify(input) },
    );
  },

  changePassword(input: ChangePasswordInput): Promise<LoginResponse> {
    return withGateway<LoginResponse>(
      "/change-password",
      "changePassword",
      { changePasswordInput: input },
      { method: "POST", body: JSON.stringify(input) },
    );
  },

  updateUserPermissions(userId: string, allowedCapabilityIds: string[]): Promise<MockUser> {
    return withGateway<MockUser>(
      `/users/${userId}/permissions`,
      "updateUserPermissions",
      { userId, allowedCapabilityIds },
      { method: "PUT", body: JSON.stringify({ allowedCapabilityIds }) },
    );
  },

  updateUserQuota(userId: string, quota: UserQuota): Promise<MockUser> {
    return withGateway<MockUser>(
      `/users/${userId}/quota`,
      "updateUserQuota",
      { userId, quota },
      { method: "PUT", body: JSON.stringify({ quota }) },
    );
  },

  listKeys(): Promise<ApiKey[]> {
    return withGateway<ApiKey[]>("/keys", "listKeys", {});
  },

  createKey(input: {
    name: string;
    env: "live" | "test";
    scopes: string[];
    ownerUserId?: string;
  }): Promise<CreatedApiKey> {
    return withGateway<CreatedApiKey>(
      "/keys",
      "createKey",
      { createInput: input },
      { method: "POST", body: JSON.stringify(input) },
    );
  },

  revokeKey(id: string): Promise<true> {
    return withGateway<true>(`/keys/${id}/revoke`, "revokeKey", { keyId: id }, { method: "POST" });
  },

  deleteKey(id: string): Promise<true> {
    return withGateway<true>(`/keys/${id}`, "deleteKey", { keyId: id }, { method: "DELETE" });
  },

  listCapabilities(): Promise<Capability[]> {
    return withGateway<Capability[]>("/capabilities", "listCapabilities", {});
  },

  getMyCapabilities(): Promise<CurrentUserCapabilitiesResponse> {
    return withGateway<CurrentUserCapabilitiesResponse>(
      "/me/capabilities",
      "getMyCapabilities",
      {},
    );
  },

  listLogs(): Promise<CallLog[]> {
    return withGateway<CallLog[]>("/logs", "listLogs", {});
  },

  debugRequest(input: DebugRequest): Promise<DebugResponse> {
    return withGateway<DebugResponse>(
      "/debug",
      "debugRequest",
      { debugInput: input },
      { method: "POST", body: JSON.stringify(input) },
    );
  },
};
