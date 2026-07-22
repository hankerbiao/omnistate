import { useEffect, useMemo, useState } from "react";
import type { MockUser, UserQuota } from "../types";
import { api } from "../services/api";
import { Badge, Button, Card, Loading, Switch, useToast } from "../components/ui";
import { formatNumber } from "../utils";

// 默认配额（用于「重置默认」）
const DEFAULT_QUOTA: UserQuota = { enabled: true, monthlyLimit: 50000, rpmLimit: 60, concurrency: 5 };

// 0 表示不限制，统一渲染为「不限」
function formatLimit(value: number): string {
  return value > 0 ? formatNumber(value) : "不限";
}

function NumField({
  label,
  hint,
  value,
  suffix,
  onChange,
}: {
  label: string;
  hint: string;
  value: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className="input-affix">
        <input
          className="input"
          type="number"
          min={0}
          step={1}
          value={value}
          onChange={(event) => {
            const raw = Math.floor(Number(event.target.value));
            onChange(Number.isFinite(raw) && raw > 0 ? raw : 0);
          }}
        />
        <span className="input-suffix">{suffix}</span>
      </div>
      <span className="field-hint">{hint}</span>
    </div>
  );
}

export function UserQuota({ users, onUpdateUser }: { users: MockUser[]; onUpdateUser: (user: MockUser) => void }) {
  const { push } = useToast();
  // 配额仅约束普通用户；管理员不受配额限制
  const manageableUsers = users.filter((user) => user.role !== "admin");
  const [selectedUserId, setSelectedUserId] = useState(manageableUsers[0]?.id ?? "");
  const selectedUser = users.find((user) => user.id === selectedUserId) ?? manageableUsers[0];

  const [draft, setDraft] = useState<UserQuota | null>(selectedUser ? { ...selectedUser.quota } : null);

  // 切换用户时，用该用户的最新配额重置草稿
  useEffect(() => {
    if (selectedUser) setDraft({ ...selectedUser.quota });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUser?.id]);

  // 当前网关返回用户配额配置；用量统计由概览接口提供，这里按配额比例展示即时预估。
  const usage = useMemo(() => {
    if (!selectedUser || selectedUser.quota.monthlyLimit <= 0) return null;
    return { monthlyUsed: Math.round(selectedUser.quota.monthlyLimit * 0.42) };
  }, [selectedUser?.id, selectedUser?.quota.monthlyLimit]);

  if (!selectedUser || !draft) return <Loading label="正在加载用户配额" />;

  const dirty = JSON.stringify(draft) !== JSON.stringify(selectedUser.quota);
  const update = (patch: Partial<UserQuota>) => setDraft((current) => (current ? { ...current, ...patch } : current));

  const save = () => {
    api.updateUserQuota(selectedUser.id, draft).then((updatedUser) => {
      onUpdateUser(updatedUser);
      push(`已保存 ${selectedUser.name} 的配额设置`, "success");
    });
  };

  const reset = () => {
    setDraft({ ...DEFAULT_QUOTA });
    push("已重置为默认配额", "info");
  };

  const monthlyPct = draft.enabled && draft.monthlyLimit > 0 && usage
    ? Math.min(100, Math.round((usage.monthlyUsed / draft.monthlyLimit) * 100))
    : 0;

  return (
    <>
      <div className="page-head">
        <h1 className="display-md">用户配额</h1>
        <p>为普通用户配置调用频率与并发额度。超出配额后平台将返回 HTTP 429，避免单一应用耗尽共享算力资源。</p>
      </div>

      <div className="permission-layout">
        <Card>
          <div className="caption-upper" style={{ marginBottom: 12 }}>普通用户</div>
          <div className="permission-user-list">
            {manageableUsers.map((user) => (
              <button
                key={user.id}
                className={`permission-user${selectedUser.id === user.id ? " active" : ""}`}
                onClick={() => setSelectedUserId(user.id)}
              >
                <span className="avatar avatar-sm">{user.avatar}</span>
                <span>
                  <strong>{user.name}</strong>
                  <small>{user.team}</small>
                </span>
                <Badge tone="muted">
                  {user.quota.enabled ? `${formatLimit(user.quota.monthlyLimit)}/月` : "不限制"}
                </Badge>
              </button>
            ))}
            {manageableUsers.length === 0 && <div className="field-hint">暂无普通用户可配置。</div>}
          </div>
        </Card>

        <Card>
          <div className="permission-head">
            <div>
              <div className="row gap-sm">
                <h2 className="heading-md">{selectedUser.name}</h2>
                <Badge tone="test">普通用户</Badge>
                {draft.enabled ? <Badge tone="success">配额生效中</Badge> : <Badge tone="muted">未启用</Badge>}
              </div>
              <p>{selectedUser.email ? `${selectedUser.email} · ` : ""}{selectedUser.team}</p>
            </div>
            <div className="row gap-sm">
              <Button variant="ghost" size="sm" onClick={reset}>重置默认</Button>
              <Button size="sm" onClick={save} disabled={!dirty}>保存配额</Button>
            </div>
          </div>

          <div className="quota-stats">
            <div className="quota-stat">
              <span className="quota-stat-label">月度调用上限</span>
              <span className="quota-stat-value">{draft.enabled ? formatLimit(draft.monthlyLimit) : "—"}<small>次</small></span>
            </div>
            <div className="quota-stat">
              <span className="quota-stat-label">每分钟请求 (RPM)</span>
              <span className="quota-stat-value">{draft.enabled ? formatLimit(draft.rpmLimit) : "—"}<small>次</small></span>
            </div>
            <div className="quota-stat">
              <span className="quota-stat-label">最大并发</span>
              <span className="quota-stat-value">{draft.enabled ? formatLimit(draft.concurrency) : "—"}<small>个</small></span>
            </div>
          </div>

          <div className="quota-switch-row">
            <div>
              <span className="label-strong">启用配额限制</span>
              <span className="label-sub">关闭后该用户不受调用上限与速率约束</span>
            </div>
            <Switch checked={draft.enabled} onChange={(value) => update({ enabled: value })} label="启用配额限制" />
          </div>

          {draft.enabled ? (
            <>
              <NumField
                label="月度调用上限"
                suffix="次 / 月"
                hint="统计自然月内的全部调用次数，0 表示不限制。"
                value={draft.monthlyLimit}
                onChange={(value) => update({ monthlyLimit: value })}
              />
              <NumField
                label="每分钟请求数 (RPM)"
                suffix="次 / 分"
                hint="单密钥每分钟允许的最大请求数，用于平滑突发流量。"
                value={draft.rpmLimit}
                onChange={(value) => update({ rpmLimit: value })}
              />
              <NumField
                label="最大并发数"
                suffix="个"
                hint="同时处于执行中的请求上限，0 表示不限制。"
                value={draft.concurrency}
                onChange={(value) => update({ concurrency: value })}
              />
            </>
          ) : (
            <div className="quota-note">
              配额限制当前<strong>未启用</strong>，{selectedUser.name} 的调用不受月度上限、速率与并发约束。启用后可在上方设置具体额度。
            </div>
          )}

          {draft.enabled && draft.monthlyLimit > 0 && usage && (
            <div className="quota-usage">
              <div className="row between" style={{ marginBottom: 6 }}>
                <span className="caption">本月已使用（演示数据）</span>
                <span className="caption">
                  {formatNumber(usage.monthlyUsed)} / {formatNumber(draft.monthlyLimit)} · {monthlyPct}%
                </span>
              </div>
              <div className="progress-track">
                <div
                  className={`progress-value${monthlyPct >= 80 ? " progress-warning" : ""}`}
                  style={{ width: `${monthlyPct}%` }}
                />
              </div>
            </div>
          )}

          <div className="quota-note">
            配额由后端在网关层强制执行：达到月度上限或触发速率 / 并发阈值时，接口将返回 <strong>HTTP 429 Too Many Requests</strong>，上游调用方应实现指数退避重试。
          </div>
        </Card>
      </div>
    </>
  );
}
