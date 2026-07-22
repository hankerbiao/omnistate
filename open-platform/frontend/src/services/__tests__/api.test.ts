import { describe, it, expect } from "vitest";
import { api } from "../api";

// 测试在 Mock 模式（__USE_MOCK__=true）下运行，覆盖 api 客户端的本地兜底逻辑。
describe("api 客户端（mock 模式）", () => {
  it("listKeys 返回种子密钥列表", async () => {
    const keys = await api.listKeys();
    expect(Array.isArray(keys)).toBe(true);
    expect(keys.length).toBeGreaterThan(0);
    expect(keys[0]).toHaveProperty("masked");
  });

  it("createKey 生成带环境前缀的明文密钥并写入列表", async () => {
    const before = await api.listKeys();
    const res = await api.createKey({
      name: "测试密钥",
      env: "live",
      scopes: ["execution_tasks:read"],
    });
    expect(res.plaintext.startsWith("dml_live_")).toBe(true);
    expect(res.key.name).toBe("测试密钥");
    expect(res.key.status).toBe("active");

    const after = await api.listKeys();
    expect(after.length).toBe(before.length + 1);
    expect(after[0].id).toBe(res.key.id);
  });

  it("revokeKey 将密钥标记为已吊销", async () => {
    const keys = await api.listKeys();
    const target = keys.find((k) => k.status === "active")!;
    await api.revokeKey(target.id);
    const after = await api.listKeys();
    expect(after.find((k) => k.id === target.id)?.status).toBe("revoked");
  });

  it("deleteKey 从列表中移除密钥", async () => {
    const before = await api.listKeys();
    const target = before[0];
    await api.deleteKey(target.id);
    const after = await api.listKeys();
    expect(after.find((k) => k.id === target.id)).toBeUndefined();
  });

  it("debugRequest 为测试环境构造 sandbox 地址，error 参数触发失败", async () => {
    const ok = await api.debugRequest({
      capabilityId: "cap_list_tasks",
      keyId: "key_01",
      env: "test",
      params: {},
    });
    expect(ok.statusCode).toBe(200);
    expect(ok.requestUrl).toContain("sandbox.dml.example.com");

    const fail = await api.debugRequest({
      capabilityId: "cap_list_tasks",
      keyId: "key_01",
      env: "live",
      params: { limit: "error" },
    });
    expect(fail.statusCode).toBe(400);
    expect(fail.responseBody).toContain("参数校验失败");
  });

  it("listUsers 与 getOverview 返回预期结构", async () => {
    const users = await api.listUsers();
    expect(users.some((u) => u.role === "admin")).toBe(true);

    const overview = await api.getOverview();
    expect(overview).toHaveProperty("totalCallsToday");
    expect(overview).toHaveProperty("daily");
  });

  it("getMyCapabilities 返回当前用户已授权能力及接口参数详情", async () => {
    window.localStorage.setItem("dml-open-platform-user", "user_developer");
    api.setConsoleUserId("user_developer");

    const result = await api.getMyCapabilities();
    expect(result.user.id).toBe("user_developer");
    expect(result.capabilities.map((item) => item.id)).toEqual([
      "cap_list_tasks",
      "cap_task_status",
      "cap_report",
    ]);

    const statusCapability = result.capabilities.find((item) => item.id === "cap_task_status");
    expect(statusCapability?.description).toBeTruthy();
    expect(statusCapability?.params[0]).toMatchObject({
      name: "task_id",
      type: "string",
      required: true,
    });
  });

  it("createUser 使用默认密码并要求首次登录改密", async () => {
    const created = await api.createUser({
      username: "firstlogin",
      role: "developer",
      allowedCapabilityIds: [],
      quota: { enabled: true, monthlyLimit: 1000, rpmLimit: 60, concurrency: 5 },
    });
    expect(created.mustChangePassword).toBe(true);
    expect(created.name).toBe("firstlogin");
    expect(created.team).toBe("未分组");

    const login = await api.login("firstlogin", "123456");
    expect(login.user.mustChangePassword).toBe(true);

    window.localStorage.setItem("dml-open-platform-user", created.id);
    const changed = await api.changePassword({
      oldPassword: "123456",
      newPassword: "firstlogin123",
    });
    expect(changed.user.mustChangePassword).toBe(false);
  });
});
