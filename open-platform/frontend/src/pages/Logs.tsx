// 调用日志页
import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import type { CallLog, MockUser } from "../types";
import { Badge, Card, CodeBlock, Empty, Loading, MethodTag, Modal } from "../components/ui";
import { formatDateTime } from "../utils";

type Filter = "all" | "success" | "error";

function StatusBadge({ log }: { log: CallLog }) {
  if (log.status === "success") return <Badge tone="success" dot>{log.statusCode}</Badge>;
  if (log.status === "client_error") return <Badge tone="warning" dot>{log.statusCode}</Badge>;
  return <Badge tone="error" dot>{log.statusCode}</Badge>;
}

export function Logs({ user }: { user: MockUser }) {
  const [logs, setLogs] = useState<CallLog[] | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [keyword, setKeyword] = useState("");
  const [selected, setSelected] = useState<CallLog | null>(null);

  useEffect(() => {
    api.listLogs().then((items) => setLogs(user.role === "admin" ? items : items.filter((log) => log.appName === "质量数据看板" || log.appName === "本地联调工作区")));
  }, [user.id]);

  const filtered = useMemo(() => {
    if (!logs) return [];
    return logs.filter((l) => {
      const okFilter =
        filter === "all" ||
        (filter === "success" && l.status === "success") ||
        (filter === "error" && l.status !== "success");
      const okKw =
        !keyword ||
        l.endpoint.includes(keyword) ||
        l.keyName.includes(keyword);
      return okFilter && okKw;
    });
  }, [logs, filter, keyword]);

  if (!logs) return <Loading />;

  const errorCount = logs.filter((l) => l.status !== "success").length;
  const avgLatency = Math.round(logs.reduce((s, l) => s + l.latencyMs, 0) / logs.length);

  return (
    <>
      <div className="page-head">
        <h1 className="display-md">调用日志</h1>
        <p>按接口、密钥和响应状态检索近期请求，快速识别失败调用、高延迟请求和异常来源。</p>
      </div>

      <div className="stats-grid stats-grid-3">
        <div className="stat-card">
          <span className="caption-upper">最近请求数</span>
          <span className="stat-value">{logs.length}</span>
        </div>
        <div className="stat-card">
          <span className="caption-upper">错误请求</span>
          <span className="stat-value" style={{ color: errorCount ? "var(--error)" : "var(--ink)" }}>
            {errorCount}
          </span>
        </div>
        <div className="stat-card">
          <span className="caption-upper">平均延迟</span>
          <span className="stat-value">{avgLatency}<span style={{ fontSize: 18 }}> ms</span></span>
        </div>
      </div>

      <div className="row between" style={{ marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <div className="segmented">
          <button aria-pressed={filter === "all"} className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>全部</button>
          <button aria-pressed={filter === "success"} className={filter === "success" ? "active" : ""} onClick={() => setFilter("success")}>成功</button>
          <button aria-pressed={filter === "error"} className={filter === "error" ? "active" : ""} onClick={() => setFilter("error")}>错误</button>
        </div>
        <input
          className="input"
          aria-label="搜索调用日志"
          style={{ maxWidth: 280 }}
          placeholder="搜索接口路径或密钥名称…"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </div>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        {filtered.length === 0 ? (
          <Empty title="没有匹配的日志" hint="尝试清空关键词，或切换到“全部”状态查看所有请求。" />
        ) : (
          <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>时间</th>
                <th>方法</th>
                <th>接口</th>
                <th>密钥</th>
                <th>状态</th>
                <th>延迟</th>
                <th>来源 IP</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((l) => (
                <tr key={l.id} className="clickable-row" onClick={() => setSelected(l)} tabIndex={0} onKeyDown={(event) => (event.key === "Enter" || event.key === " ") && setSelected(l)}>
                  <td className="mono text-muted" style={{ whiteSpace: "nowrap" }}>{formatDateTime(l.timestamp)}</td>
                  <td><MethodTag method={l.method} /></td>
                  <td><code className="mono" style={{ color: "var(--body-strong)" }}>{l.endpoint}</code></td>
                  <td>{l.keyName}</td>
                  <td><StatusBadge log={l} /></td>
                  <td className={l.latencyMs > 500 ? "" : ""} style={{ color: l.latencyMs > 500 ? "var(--warning)" : "var(--body)" }}>
                    {l.latencyMs} ms
                  </td>
                  <td className="mono text-muted">{l.ip}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </Card>

      {selected && (
        <Modal title="调用详情与诊断" onClose={() => setSelected(null)} width={760}>
          <div className="log-detail-grid">
            <DetailItem label="Request ID" value={selected.requestId} mono />
            <DetailItem label="应用" value={selected.appName} />
            <DetailItem label="API 密钥" value={selected.keyName} />
            <DetailItem label="来源 IP" value={selected.ip} mono />
            <DetailItem label="总耗时" value={`${selected.latencyMs} ms`} />
            <DetailItem label="网关耗时" value={`${selected.gatewayLatencyMs} ms`} />
          </div>
          <div className="debug-method-line" style={{ marginTop: 16 }}>
            <MethodTag method={selected.method} />
            <code className="mono">{selected.endpoint}</code>
            <span style={{ marginLeft: "auto" }}><StatusBadge log={selected} /></span>
          </div>
          {selected.diagnosis && (
            <div className="diagnosis-panel">
              <div className="row between" style={{ marginBottom: 6 }}>
                <strong>问题诊断</strong>
                {selected.errorCode && <Badge tone="error">{selected.errorCode}</Badge>}
              </div>
              <p>{selected.diagnosis}</p>
            </div>
          )}
          {selected.requestBody && <div style={{ marginTop: 18 }}><div className="caption-upper" style={{ marginBottom: 8 }}>请求体</div><CodeBlock language="json" code={selected.requestBody} /></div>}
          <div style={{ marginTop: 18 }}><div className="caption-upper" style={{ marginBottom: 8 }}>响应体</div><CodeBlock language="json" code={selected.responseBody} /></div>
        </Modal>
      )}
    </>
  );
}

function DetailItem({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong className={mono ? "mono" : ""}>{value}</strong>
    </div>
  );
}
