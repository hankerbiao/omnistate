import { useEffect, useMemo, useState } from "react";
import type { Capability, CreateUserInput, MockUser, UserRole } from "../types";
import { api } from "../services/api";
import { Badge, Button, Card, Loading, MethodTag, Modal, useToast } from "../components/ui";

export function UserPermissions({
  users,
  onUpdateUser,
  onCreateUser,
}: {
  users: MockUser[];
  onUpdateUser: (user: MockUser) => void;
  onCreateUser: (user: MockUser) => void;
}) {
  const { push } = useToast();
  const [capabilities, setCapabilities] = useState<Capability[] | null>(null);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const manageableUsers = users.filter((user) => user.role !== "admin");
  const [selectedUserId, setSelectedUserId] = useState(manageableUsers[0]?.id ?? "");
  const selectedUser = users.find((user) => user.id === selectedUserId) ?? manageableUsers[0];
  const [selectedIds, setSelectedIds] = useState<string[]>(selectedUser?.allowedCapabilityIds ?? []);

  useEffect(() => {
    api.listCapabilities().then(setCapabilities);
  }, []);

  useEffect(() => {
    setSelectedIds(selectedUser?.allowedCapabilityIds ?? []);
  }, [selectedUser?.id, selectedUser?.allowedCapabilityIds]);

  const categories = useMemo(() => {
    if (!capabilities) return [];
    return Array.from(new Set(capabilities.map((capability) => capability.category)));
  }, [capabilities]);

  if (!capabilities || !selectedUser) return <Loading label="正在加载用户权限" />;

  const toggle = (id: string) => {
    setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  const save = () => {
    api.updateUserPermissions(selectedUser.id, selectedIds).then((updatedUser) => {
      onUpdateUser(updatedUser);
      push(`已更新 ${selectedUser.name} 的接口权限`, "success");
    });
  };

  return (
    <>
      <div className="page-head">
        <h1 className="display-md">用户接口权限</h1>
        <p>管理员可以精确控制普通用户能够查看和调用的具体接口。配置会同步影响开放能力目录和 API 调试台。</p>
        <div style={{ marginTop: 16 }}>
          <Button onClick={() => setShowCreateUser(true)}>添加用户</Button>
        </div>
      </div>

      <div className="permission-layout">
        <Card>
          <div className="caption-upper" style={{ marginBottom: 12 }}>普通用户</div>
          <div className="permission-user-list">
            {manageableUsers.map((user) => (
              <button key={user.id} className={`permission-user${selectedUser.id === user.id ? " active" : ""}`} onClick={() => setSelectedUserId(user.id)}>
                <span className="avatar avatar-sm">{user.avatar}</span>
                <span><strong>{user.name}</strong><small>{user.team}</small></span>
                <Badge tone="muted">{user.allowedCapabilityIds.length} 项</Badge>
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <div className="permission-head">
            <div>
              <div className="row gap-sm"><h2 className="heading-md">{selectedUser.name}</h2><Badge tone="test">普通用户</Badge></div>
              <p>{selectedUser.email ? `${selectedUser.email} · ` : ""}{selectedUser.team}</p>
            </div>
            <div className="row gap-sm">
              <Button variant="ghost" size="sm" onClick={() => setSelectedIds(capabilities.map((item) => item.id))}>全部允许</Button>
              <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>全部取消</Button>
              <Button size="sm" onClick={save}>保存权限</Button>
            </div>
          </div>

          <div className="permission-summary">
            <strong>{selectedIds.length}</strong>
            <span>已授权接口</span>
            <small>共 {capabilities.length} 个开放接口</small>
          </div>

          {categories.map((category) => {
            const items = capabilities.filter((capability) => capability.category === category);
            const selectedCount = items.filter((item) => selectedIds.includes(item.id)).length;
            return (
              <section className="permission-group" key={category}>
                <div className="row between permission-group-head">
                  <div><strong>{category}</strong><span>{selectedCount} / {items.length} 已授权</span></div>
                  <button onClick={() => {
                    const ids = items.map((item) => item.id);
                    const allSelected = ids.every((id) => selectedIds.includes(id));
                    setSelectedIds((current) => allSelected ? current.filter((id) => !ids.includes(id)) : Array.from(new Set([...current, ...ids])));
                  }}>{selectedCount === items.length ? "取消本组" : "允许本组"}</button>
                </div>
                <div className="permission-cap-list">
                  {items.map((capability) => {
                    const checked = selectedIds.includes(capability.id);
                    return (
                      <button key={capability.id} className={`permission-cap${checked ? " active" : ""}`} aria-pressed={checked} onClick={() => toggle(capability.id)}>
                        <span className="scope-check">{checked ? "✓" : ""}</span>
                        <MethodTag method={capability.method} />
                        <span className="permission-cap-copy">
                          <strong>{capability.name}</strong>
                          <code>{capability.path}</code>
                          <small>{capability.summary}</small>
                        </span>
                        <Badge tone="muted">{capability.scope}</Badge>
                      </button>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </Card>
      </div>

      {showCreateUser && (
        <CreateUserModal
          capabilities={capabilities}
          onClose={() => setShowCreateUser(false)}
          onCreated={(created) => {
            onCreateUser(created);
            setSelectedUserId(created.role === "admin" ? selectedUserId : created.id);
            setShowCreateUser(false);
            push(`已添加用户 ${created.name}`, "success");
          }}
        />
      )}
    </>
  );
}

function CreateUserModal({
  capabilities,
  onClose,
  onCreated,
}: {
  capabilities: Capability[];
  onClose: () => void;
  onCreated: (user: MockUser) => void;
}) {
  const { push } = useToast();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<UserRole>("developer");
  const [allowedCapabilityIds, setAllowedCapabilityIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const input: CreateUserInput = {
    username,
    role,
    allowedCapabilityIds,
    quota: { enabled: true, monthlyLimit: 100000, rpmLimit: 120, concurrency: 10 },
  };

  const toggleCapability = (id: string) => {
    setAllowedCapabilityIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const submit = async () => {
    if (!username.trim()) {
      push("请填写用户名", "error");
      return;
    }
    setBusy(true);
    try {
      const created = await api.createUser(input);
      onCreated(created);
    } catch (error) {
      push(error instanceof Error ? error.message : "添加用户失败", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="添加用户"
      onClose={onClose}
      width={720}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose}>取消</Button>
          <Button onClick={submit} disabled={busy}>{busy ? "添加中..." : "添加用户"}</Button>
        </>
      )}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
        <div className="field">
          <label className="field-label" htmlFor="new-username">用户名</label>
          <input id="new-username" className="input" value={username} onChange={(event) => setUsername(event.target.value)} />
          <span className="field-hint">姓名默认使用用户名，团队默认为未分组。</span>
        </div>
        <div className="field">
          <label className="field-label">角色</label>
          <div className="segmented">
            <button type="button" className={role === "developer" ? "active" : ""} onClick={() => setRole("developer")}>普通用户</button>
            <button type="button" className={role === "admin" ? "active" : ""} onClick={() => setRole("admin")}>管理员</button>
          </div>
        </div>
      </div>

      <div className="quota-note" style={{ marginTop: 0, marginBottom: 18 }}>
        新用户初始密码为 <strong>123456</strong>，首次登录后必须修改密码才能继续使用控制台。
      </div>

      <div className="field" style={{ marginBottom: 0 }}>
        <label className="field-label">默认接口权限</label>
        <div className="permission-cap-list" style={{ maxHeight: 260, overflow: "auto" }}>
          {capabilities.map((capability) => {
            const checked = allowedCapabilityIds.includes(capability.id);
            return (
              <button key={capability.id} className={`permission-cap${checked ? " active" : ""}`} onClick={() => toggleCapability(capability.id)}>
                <span className="scope-check">{checked ? "✓" : ""}</span>
                <MethodTag method={capability.method} />
                <span className="permission-cap-copy"><strong>{capability.name}</strong><code>{capability.path}</code></span>
                <Badge tone="muted">{capability.scope}</Badge>
              </button>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}
