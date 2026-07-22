import { useState } from "react";
import { Button, Card, useToast } from "../components/ui";
import { api } from "../services/api";
import type { MockUser } from "../types";

export function ForceChangePassword({
  user,
  onChanged,
  onLogout,
}: {
  user: MockUser;
  onChanged: (user: MockUser) => void;
  onLogout: () => void;
}) {
  const { push } = useToast();
  const [oldPassword, setOldPassword] = useState("123456");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!oldPassword || !newPassword || !confirmPassword) {
      push("请完整填写密码", "error");
      return;
    }
    if (newPassword !== confirmPassword) {
      push("两次输入的新密码不一致", "error");
      return;
    }
    if (newPassword === "123456") {
      push("新密码不能继续使用默认密码", "error");
      return;
    }
    if (newPassword === oldPassword) {
      push("新密码不能与原密码相同", "error");
      return;
    }

    setBusy(true);
    try {
      const result = await api.changePassword({ oldPassword, newPassword });
      onChanged(result.user);
      push("密码已更新", "success");
    } catch (error) {
      push(error instanceof Error ? error.message : "修改密码失败", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-shell">
      <section className="login-panel">
        <div className="login-copy">
          <div className="caption-upper">First Login</div>
          <h1 className="display-lg">请先修改初始密码</h1>
          <p className="body-md text-muted">
            当前账号 {user.username ?? user.name} 使用系统默认密码。完成修改后即可进入开放平台控制台。
          </p>
        </div>

        <Card style={{ width: "100%", maxWidth: 420 }}>
          <form className="login-form" onSubmit={submit}>
            <div>
              <h2 className="heading-md">修改密码</h2>
              <p className="body-sm text-muted" style={{ margin: "6px 0 0" }}>
                新密码不能为默认密码 123456。
              </p>
            </div>

            <div className="field">
              <label className="field-label" htmlFor="old-password">当前密码</label>
              <input
                id="old-password"
                className="input"
                type="password"
                value={oldPassword}
                onChange={(event) => setOldPassword(event.target.value)}
                autoComplete="current-password"
                autoFocus
              />
            </div>

            <div className="field">
              <label className="field-label" htmlFor="new-password">新密码</label>
              <input
                id="new-password"
                className="input"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
              />
            </div>

            <div className="field">
              <label className="field-label" htmlFor="confirm-password">确认新密码</label>
              <input
                id="confirm-password"
                className="input"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
              />
            </div>

            <div className="row gap-sm">
              <Button type="submit" disabled={busy}>{busy ? "提交中..." : "修改密码"}</Button>
              <Button variant="secondary" onClick={onLogout}>退出登录</Button>
            </div>
          </form>
        </Card>
      </section>
    </div>
  );
}
