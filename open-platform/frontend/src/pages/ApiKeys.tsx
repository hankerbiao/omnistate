// API 密钥管理页（核心功能）
import { useEffect, useState } from "react";
import { api } from "../services/api";
import { AVAILABLE_SCOPES } from "../config/scopes";
import type { ApiKey, CreatedApiKey, MockUser } from "../types";
import {
  Badge,
  Button,
  Card,
  CopyButton,
  Empty,
  Loading,
  Modal,
  useToast,
} from "../components/ui";
import { IconPlus, IconCheck, IconTrash, IconKey } from "../components/icons";
import { formatDateTime, timeAgo, formatNumber } from "../utils";

export function ApiKeys({ user }: { user: MockUser }) {
  const { push } = useToast();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [created, setCreated] = useState<CreatedApiKey | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<ApiKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [users, setUsers] = useState<MockUser[]>([]);

  const load = () => api.listKeys().then(setKeys);
  useEffect(() => {
    load();
  }, [user.id]);

  useEffect(() => {
    if (user.role === "admin") api.listUsers().then(setUsers);
  }, [user.role]);

  const handleCreated = (res: CreatedApiKey) => {
    setShowCreate(false);
    setCreated(res);
    load();
  };

  const doRevoke = async () => {
    if (!confirmRevoke) return;
    setBusy(true);
    await api.revokeKey(confirmRevoke.id);
    setBusy(false);
    setConfirmRevoke(null);
    push("密钥已吊销", "success");
    load();
  };

  return (
    <>
      <div className="page-head row between" style={{ alignItems: "flex-start" }}>
        <div>
          <h1 className="display-md">API 密钥</h1>
          <p>
            为每个系统创建独立凭据，并按环境与能力分配最小权限。密钥明文仅展示一次，请立即安全保存。
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <IconPlus />
          新建密钥
        </Button>
      </div>

      {!keys ? (
        <Loading />
      ) : keys.length === 0 ? (
        <Card>
          <Empty title="还没有 API 密钥" hint="点击右上角「新建密钥」开始接入开放平台。" />
        </Card>
      ) : (
        <Card style={{ padding: 0, overflow: "hidden" }}>
          <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>密钥</th>
                <th>环境</th>
                <th>权限范围</th>
                <th>今日调用</th>
                <th>最近使用</th>
                <th>状态</th>
                <th style={{ textAlign: "right" }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td>
                    <div style={{ fontWeight: 500, color: "var(--ink)" }}>{k.name}</div>
                    <div className="caption text-muted">
                      {user.role === "admin" ? `${ownerName(k.ownerUserId, users)} · ` : ""}
                      创建于 {formatDateTime(k.createdAt).slice(0, 10)}
                    </div>
                  </td>
                  <td>
                    <div className="row gap-xs">
                      <code className="mono" style={{ color: "var(--body)" }}>{k.masked}</code>
                      <CopyButton text={k.masked} />
                    </div>
                  </td>
                  <td>
                    <Badge tone={k.env === "live" ? "live" : "test"}>
                      {k.env === "live" ? "生产" : "测试"}
                    </Badge>
                  </td>
                  <td>
                    <div className="row gap-xs" style={{ flexWrap: "wrap", maxWidth: 200 }}>
                      {k.scopes.map((s) => (
                        <Badge key={s} tone="muted">{s}</Badge>
                      ))}
                    </div>
                  </td>
                  <td>{k.status === "active" ? formatNumber(k.callsToday) : "—"}</td>
                  <td>
                    {k.lastUsedAt ? (
                      <span title={formatDateTime(k.lastUsedAt)}>{timeAgo(k.lastUsedAt)}</span>
                    ) : (
                      <span className="text-muted">从未使用</span>
                    )}
                  </td>
                  <td>
                    {k.status === "active" ? (
                      <Badge tone="success" dot>启用</Badge>
                    ) : (
                      <Badge tone="error" dot>已吊销</Badge>
                    )}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {k.status === "active" ? (
                      <Button variant="danger" size="sm" onClick={() => setConfirmRevoke(k)}>
                        吊销
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={async () => {
                          await api.deleteKey(k.id);
                          push("已删除记录", "info");
                          load();
                        }}
                      >
                        <IconTrash />
                        删除
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Card>
      )}

      {showCreate && (
        <CreateKeyModal
          user={user}
          users={users}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {created && <RevealKeyModal created={created} onClose={() => setCreated(null)} />}

      {confirmRevoke && (
        <Modal
          title="吊销密钥"
          onClose={() => setConfirmRevoke(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setConfirmRevoke(null)}>取消</Button>
              <Button variant="primary" onClick={doRevoke} disabled={busy}>
                {busy ? "处理中…" : "确认吊销"}
              </Button>
            </>
          }
        >
          <p className="body-md">
            确认吊销密钥 <strong style={{ color: "var(--ink)" }}>{confirmRevoke.name}</strong>？
          </p>
          <p className="body-sm text-muted" style={{ marginTop: 8 }}>
            吊销后使用该密钥的所有外部请求将立即返回 401，且不可恢复。
          </p>
        </Modal>
      )}
    </>
  );
}

/* ---------- 新建密钥弹窗 ---------- */
function CreateKeyModal({
  user,
  users,
  onClose,
  onCreated,
}: {
  user: MockUser;
  users: MockUser[];
  onClose: () => void;
  onCreated: (r: CreatedApiKey) => void;
}) {
  const { push } = useToast();
  const [name, setName] = useState("");
  const [env, setEnv] = useState<"live" | "test">("live");
  const [scopes, setScopes] = useState<string[]>(["execution_tasks:read"]);
  const [ownerUserId, setOwnerUserId] = useState(user.id);
  const [busy, setBusy] = useState(false);

  const toggle = (id: string) =>
    setScopes((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));

  const submit = async () => {
    if (!name.trim()) {
      push("请填写密钥名称", "error");
      return;
    }
    if (scopes.length === 0) {
      push("请至少选择一个权限范围", "error");
      return;
    }
    setBusy(true);
    const res = await api.createKey({
      name: name.trim(),
      env,
      scopes,
      ownerUserId: user.role === "admin" ? ownerUserId : user.id,
    });
    setBusy(false);
    onCreated(res);
  };

  return (
    <Modal
      title="新建 API 密钥"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>取消</Button>
          <Button onClick={submit} disabled={busy}>
            {busy ? "创建中…" : "创建密钥"}
          </Button>
        </>
      }
    >
      <div className="field">
        <label className="field-label" htmlFor="api-key-name">密钥名称</label>
        <input
          id="api-key-name"
          className="input"
          placeholder="例如：CI 流水线集成"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
        <span className="field-hint">便于识别用途，仅在平台内部显示。</span>
      </div>

      <div className="field">
        <label className="field-label">环境</label>
        <div className="segmented">
          <button type="button" className={env === "live" ? "active" : ""} aria-pressed={env === "live"} onClick={() => setEnv("live")}>
            生产（live）
          </button>
          <button type="button" className={env === "test" ? "active" : ""} aria-pressed={env === "test"} onClick={() => setEnv("test")}>
            测试（test）
          </button>
        </div>
      </div>

      {user.role === "admin" && users.length > 0 && (
        <div className="field">
          <label className="field-label" htmlFor="api-key-owner">归属用户</label>
          <select
            id="api-key-owner"
            className="input"
            value={ownerUserId}
            onChange={(event) => setOwnerUserId(event.target.value)}
          >
            {users.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.team}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="field" style={{ marginBottom: 0 }}>
        <label className="field-label">权限范围</label>
        <span className="field-hint" style={{ marginBottom: 4 }}>
          密钥能访问的开放能力将受此范围限制，遵循最小权限原则。
        </span>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {AVAILABLE_SCOPES.map((s) => {
            const checked = scopes.includes(s.id);
            return (
              <button
                type="button"
                key={s.id}
                className={`scope-option${checked ? " checked" : ""}`}
                aria-pressed={checked}
                onClick={() => toggle(s.id)}
              >
                <span className="scope-check">{checked && <IconCheck />}</span>
                <div>
                  <div className="row gap-xs">
                    <span className="title-sm">{s.label}</span>
                    <code className="mono text-muted">{s.id}</code>
                  </div>
                  <div className="body-sm text-muted">{s.desc}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}

function ownerName(ownerUserId: string, users: MockUser[]): string {
  return users.find((item) => item.id === ownerUserId)?.name ?? ownerUserId;
}

/* ---------- 明文展示弹窗（仅一次） ---------- */
function RevealKeyModal({
  created,
  onClose,
}: {
  created: CreatedApiKey;
  onClose: () => void;
}) {
  return (
    <Modal
      title="密钥创建成功"
      onClose={onClose}
      footer={<Button onClick={onClose}>我已妥善保存</Button>}
    >
      <div
        className="row gap-xs"
        style={{
          padding: "12px 14px",
          background: "rgba(212,160,23,0.1)",
          borderRadius: "var(--r-md)",
          marginBottom: 20,
        }}
      >
        <span className="body-sm" style={{ color: "#a67c0d" }}>
          ⚠ 明文密钥仅此一次完整展示。关闭后将无法再次查看，请立即复制并安全保存。
        </span>
      </div>

      <div className="field" style={{ marginBottom: 0 }}>
        <label className="field-label">
          <IconKey size={14} style={{ marginRight: 6, color: "var(--primary)" }} />
          {created.key.name}
        </label>
        <div
          className="code-block"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}
        >
          <code style={{ wordBreak: "break-all", fontFamily: "var(--font-mono)", fontSize: 13 }}>
            {created.plaintext}
          </code>
        </div>
        <div style={{ marginTop: 14 }}>
          <CopyButton text={created.plaintext} label="复制完整密钥" />
        </div>
      </div>
    </Modal>
  );
}
