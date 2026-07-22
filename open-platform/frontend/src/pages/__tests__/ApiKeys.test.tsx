import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToastProvider } from "../../components/ui";
import { ApiKeys } from "../ApiKeys";
import type { MockUser } from "../../types";

const admin: MockUser = {
  id: "user_admin",
  username: "admin",
  name: "李彪",
  email: "libiao@dml.local",
  role: "admin",
  team: "DML 平台管理员",
  avatar: "李",
  allowedCapabilityIds: [],
  quota: { enabled: true, monthlyLimit: 0, rpmLimit: 0, concurrency: 0 },
  mustChangePassword: false,
};

function renderKeys(user: MockUser) {
  return render(
    <ToastProvider>
      <ApiKeys user={user} />
    </ToastProvider>,
  );
}

describe("ApiKeys 页面", () => {
  it("渲染标题并在加载后展示密钥列表", async () => {
    renderKeys(admin);
    expect(screen.getByText("API 密钥")).toBeInTheDocument();
    expect(await screen.findByText("CI 流水线集成")).toBeInTheDocument();
  });

  it("非管理员可以管理自己的密钥", async () => {
    const dev: MockUser = { ...admin, id: "user_developer", username: "developer", role: "developer" };
    renderKeys(dev);
    await screen.findByText("本地联调（测试）");
    expect(screen.getByText("新建密钥")).toBeInTheDocument();
  });

  it("管理员可打开新建弹窗并创建密钥（展示明文）", async () => {
    const user = userEvent.setup();
    renderKeys(admin);
    await screen.findByText("CI 流水线集成");

    await user.click(screen.getByText("新建密钥"));
    const nameInput = await screen.findByLabelText("密钥名称");
    await user.type(nameInput, "端到端测试密钥");
    await user.click(screen.getByText("创建密钥"));

    expect(await screen.findByText("密钥创建成功")).toBeInTheDocument();
    expect(screen.getByText(/端到端测试密钥/)).toBeInTheDocument();
  });
});
