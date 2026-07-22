// DML V4 开放平台 · Mock 处理层
// 注意：本模块仅在与网关断开（USE_MOCK=true）时由 api.ts 动态加载，
// 生产构建默认不会打包此处逻辑（见 vite.config.ts 的 __USE_MOCK__ define）。
import type { ApiKey, ChangePasswordInput, CreateUserInput, DebugRequest, MockUser, UserQuota } from "../types";
import { mockApiKeys, mockCapabilities, mockLogs, mockOverview, mockUsers } from "./data";

// 可变 mock 状态（模拟服务端内存数据）
let keys: ApiKey[] = [...mockApiKeys];
let users: MockUser[] = [...mockUsers];

let passwordByUsername: Record<string, string> = {
  admin: "admin123",
  developer: "password123",
  zhaolei: "password123",
};

function delay<T>(value: T, ms = 420): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function randomHex(len: number): string {
  const chars = "0123456789abcdef";
  let out = "";
  for (let i = 0; i < len; i += 1) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

export type MockOp =
  | "login"
  | "getOverview"
  | "listUsers"
  | "createUser"
  | "changePassword"
  | "updateUserPermissions"
  | "updateUserQuota"
  | "listKeys"
  | "createKey"
  | "revokeKey"
  | "deleteKey"
  | "listCapabilities"
  | "getMyCapabilities"
  | "listLogs"
  | "debugRequest";

export type MockArgs = {
  loginInput?: { username: string; password: string };
  userId?: string;
  createUserInput?: CreateUserInput;
  changePasswordInput?: ChangePasswordInput;
  allowedCapabilityIds?: string[];
  quota?: UserQuota;
  createInput?: { name: string; env: "live" | "test"; scopes: string[]; ownerUserId?: string };
  keyId?: string;
  debugInput?: DebugRequest;
};

export async function runMock<T>(op: MockOp, args: MockArgs = {}): Promise<T> {
  switch (op) {
    case "login": {
      const input = args.loginInput!;
      const username = input.username.trim().toLowerCase();
      const user = users.find((item) => item.username === username);
      if (!user || passwordByUsername[username] !== input.password) throw new Error("用户名或密码错误");
      return delay({ user }) as Promise<T>;
    }

    case "getOverview":
      return delay(mockOverview) as Promise<T>;

    case "listUsers":
      return delay([...users]) as Promise<T>;

    case "createUser": {
      const input = args.createUserInput!;
      const username = input.username.trim().toLowerCase();
      if (users.some((user) => user.username === username)) throw new Error("用户名已存在");
      const user: MockUser = {
        id: `user_${randomHex(8)}`,
        username,
        name: username,
        email: "",
        role: input.role,
        team: "未分组",
        avatar: username[0].toUpperCase(),
        allowedCapabilityIds: input.allowedCapabilityIds,
        quota: input.quota,
        mustChangePassword: true,
      };
      users = [...users, user];
      passwordByUsername = { ...passwordByUsername, [username]: "123456" };
      return delay(user) as Promise<T>;
    }

    case "changePassword": {
      const input = args.changePasswordInput!;
      const currentUserId = window.localStorage.getItem("dml-open-platform-user") ?? "user_admin";
      const user = users.find((item) => item.id === currentUserId);
      const username = user?.username ?? "";
      if (!user || !username || passwordByUsername[username] !== input.oldPassword) {
        throw new Error("原密码不正确");
      }
      if (input.newPassword === "123456") throw new Error("新密码不能继续使用默认密码");
      if (input.newPassword === input.oldPassword) throw new Error("新密码不能与原密码相同");
      const updated = { ...user, mustChangePassword: false };
      users = users.map((item) => (item.id === user.id ? updated : item));
      passwordByUsername = { ...passwordByUsername, [username]: input.newPassword };
      return delay({ user: updated }) as Promise<T>;
    }

    case "updateUserPermissions": {
      users = users.map((user) =>
        user.id === args.userId
          ? { ...user, allowedCapabilityIds: args.allowedCapabilityIds ?? [] }
          : user,
      );
      const updated = users.find((user) => user.id === args.userId);
      if (!updated) throw new Error("未找到用户");
      return delay(updated) as Promise<T>;
    }

    case "updateUserQuota": {
      users = users.map((user) =>
        user.id === args.userId ? { ...user, quota: args.quota! } : user,
      );
      const updated = users.find((user) => user.id === args.userId);
      if (!updated) throw new Error("未找到用户");
      return delay(updated) as Promise<T>;
    }

    case "listKeys":
      return delay([...keys]) as Promise<T>;

    case "createKey": {
      const input = args.createInput!;
      const prefix = input.env === "live" ? "dml_live_" : "dml_test_";
      const body = randomHex(32);
      const plaintext = `${prefix}${body}`;
      const key: ApiKey = {
        id: `key_${randomHex(6)}`,
        name: input.name,
        ownerUserId: input.ownerUserId ?? "user_admin",
        prefix,
        masked: `${prefix}${body.slice(0, 4)}${"*".repeat(10)}${body.slice(-4)}`,
        status: "active",
        scopes: input.scopes,
        createdAt: new Date().toISOString(),
        lastUsedAt: null,
        callsToday: 0,
        env: input.env,
      };
      keys = [key, ...keys];
      return delay({ key, plaintext }) as Promise<T>;
    }

    case "revokeKey": {
      keys = keys.map((key) =>
        key.id === args.keyId ? { ...key, status: "revoked" as const, callsToday: 0 } : key,
      );
      return delay(true) as Promise<T>;
    }

    case "deleteKey": {
      keys = keys.filter((key) => key.id !== args.keyId);
      return delay(true) as Promise<T>;
    }

    case "listCapabilities":
      return delay(mockCapabilities) as Promise<T>;

    case "getMyCapabilities": {
      const currentUserId = window.localStorage.getItem("dml-open-platform-user") ?? "user_admin";
      const user = users.find((item) => item.id === currentUserId) ?? users[0];
      const capabilities =
        user.role === "admin"
          ? mockCapabilities
          : mockCapabilities.filter((item) => user.allowedCapabilityIds.includes(item.id));
      return delay({ user, capabilities }) as Promise<T>;
    }

    case "listLogs":
      return delay(mockLogs) as Promise<T>;

    case "debugRequest": {
      const input = args.debugInput!;
      const capability = mockCapabilities.find((item) => item.id === input.capabilityId);
      if (!capability) throw new Error("未找到开放能力");
      const resolvedPath = capability.path.replace(
        /\{(\w+)\}/g,
        (_, name: string) => input.params[name] || `{${name}}`,
      );
      const query =
        capability.method === "GET"
          ? Object.entries(input.params)
              .filter(([name, value]) => value && !capability.path.includes(`{${name}}`))
              .map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`)
              .join("&")
          : "";
      const requestUrl = `https://${input.env === "live" ? "open" : "sandbox"}.dml.example.com${resolvedPath}${query ? `?${query}` : ""}`;
      const shouldFail = Object.values(input.params).some((value) =>
        value.toLowerCase().includes("error"),
      );
      return delay(
        {
          requestId: `req_debug_${randomHex(8)}`,
          statusCode: shouldFail ? 400 : 200,
          latencyMs: shouldFail ? 46 : 128,
          requestUrl,
          responseBody: shouldFail
            ? JSON.stringify(
                { code: 400, message: "参数校验失败", hint: "将参数中的 error 替换为有效值后重试" },
                null,
                2,
              )
            : capability.sampleResponse,
        },
        780,
      ) as Promise<T>;
    }

    default:
      throw new Error(`未知 mock 操作: ${op}`);
  }
}
