// 开放能力目录页 — Supabaze 风格
import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import type { Capability, MockUser } from "../types";
import {
  Badge,
  Card,
  CodeBlock,
  CopyButton,
  Loading,
  MethodTag,
} from "../components/ui";
import { IconChevron } from "../components/icons";

const MODULE_META: Record<string, { intro: string; response: string }> = {
  测试任务: {
    intro: "面向 CI/CD、外部质量平台和自动化调度系统，提供任务下发、重跑、进度查询与执行轨迹读取能力。",
    response: "响应通常返回任务 ID、整体状态、进度、用例通过/失败统计或时间线事件，所有数据均受 API Key 所属账号和 scope 约束。",
  },
  测试资产: {
    intro: "用于同步 DML 中的测试用例资产，包括用例列表、详情和变更审计记录。",
    response: "响应返回用例基础信息、步骤、优先级、状态、关联需求以及变更记录，适合外部门户、质量看板和资产同步任务消费。",
  },
  测试需求: {
    intro: "用于读取测试需求列表与详情，帮助外部系统建立需求到测试资产的追踪关系。",
    response: "响应返回需求标题、优先级、状态、描述、验收标准、风险点和负责人等字段，便于做测试覆盖分析。",
  },
  项目: {
    intro: "用于读取项目基础信息、统计概览、风险阻塞项和最近动态，是外部项目看板的主要数据入口。",
    response: "响应包含项目列表、项目详情、统计指标、阻塞项或活动记录，可直接用于项目质量态势展示。",
  },
  报告分析: {
    intro: "将执行状态与时间线聚合成报告摘要，面向测试报告同步、失败归因和质量复盘场景。",
    response: "响应返回通过率、耗时、总数、通过/失败数量、失败原因聚类以及原始状态和时间线摘要。",
  },
  集成: {
    intro: "提供平台到外部系统的事件集成能力，目前支持注册任务结果回调地址。",
    response: "响应返回 webhook ID、状态、订阅事件和创建时间，后续任务完成事件会按注册配置推送。",
  },
};

function moduleMeta(category: string) {
  return MODULE_META[category] ?? {
    intro: "该模块提供一组可通过开放平台 API Key 调用的 DML 能力。",
    response: "响应统一使用开放平台信封格式，业务数据位于 data 字段中。",
  };
}

function groupedByCategory(capabilities: Capability[]) {
  return capabilities.reduce<Record<string, Capability[]>>((groups, capability) => {
    const current = groups[capability.category] ?? [];
    groups[capability.category] = [...current, capability];
    return groups;
  }, {});
}

function samplePath(path: string) {
  return path
    .replace("{task_id}", "ET-2026-000128")
    .replace("{case_id}", "TC-2026-0451")
    .replace("{req_id}", "REQ-2026-0012")
    .replace("{project_id}", "PROJ-001")
    .replace(/\{(\w+)\}/g, "$1-demo");
}

export function Capabilities({ user }: { user: MockUser }) {
  const [caps, setCaps] = useState<Capability[] | null>(null);
  const [active, setActive] = useState<string>("全部");
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    api.getMyCapabilities().then((result) => {
      setCaps(result.capabilities);
      setOpenId(result.capabilities[0]?.id ?? null);
    });
  }, [user.id, user.allowedCapabilityIds]);

  const categories = useMemo(() => {
    if (!caps) return ["全部"];
    return ["全部", ...Array.from(new Set(caps.map((c) => c.category)))];
  }, [caps]);

  const filtered = useMemo(() => {
    if (!caps) return [];
    return active === "全部" ? caps : caps.filter((c) => c.category === active);
  }, [caps, active]);

  const grouped = useMemo(() => groupedByCategory(filtered), [filtered]);
  const visibleCategories = useMemo(
    () => categories.filter((category) => category !== "全部" && grouped[category]?.length),
    [categories, grouped],
  );

  if (!caps) return <Loading />;

  return (
    <>
      {/* 页面头部 */}
      <div className="page-head">
        <h1 className="display-md">开放能力目录</h1>
        <p>
          {user.role === "admin" ? "查看平台全部开放接口及其权限要求、请求参数和调用示例。" : `当前账号已获授权 ${caps.length} 个接口，可展开查看参数并复制调用示例。`} 所有接口统一使用
          <code className="mono" style={{ margin: "0 4px" }}>{"{ code, data }"}</code>
          响应格式。
        </p>
      </div>

      {/* API 基址提示 */}
      <Card style={{ marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div className="caption-upper">API 基础地址</div>
          <code className="mono" style={{ fontSize: 15, color: "var(--ink)" }}>
            https://open.dml.example.com
          </code>
        </div>
        <CopyButton text="https://open.dml.example.com" label="复制" />
      </Card>

      {/* 分类标签 */}
      <div className="row gap-xs" style={{ marginBottom: 20, flexWrap: "wrap" }}>
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setActive(c)}
            className="btn btn-sm"
            aria-pressed={active === c}
            style={{
              background: active === c ? "var(--canvas-soft)" : "transparent",
              color: active === c ? "var(--ink)" : "var(--muted)",
              border: "1px solid " + (active === c ? "var(--hairline)" : "var(--hairline)"),
              fontWeight: active === c ? 500 : 400,
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* 能力列表 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        {visibleCategories.map((category) => {
          const items = grouped[category] ?? [];
          const meta = moduleMeta(category);
          return (
            <section key={category} aria-labelledby={`module-${category}`}>
              <div style={{ marginBottom: 12 }}>
                <div className="row gap-sm" style={{ alignItems: "center", marginBottom: 8 }}>
                  <h2 id={`module-${category}`} className="title-md" style={{ margin: 0 }}>{category}</h2>
                  <Badge tone="muted">{items.length} 个接口</Badge>
                </div>
                <p className="body-md text-muted" style={{ margin: 0, maxWidth: 880 }}>{meta.intro}</p>
                <p className="body-sm text-muted-soft" style={{ margin: "6px 0 0", maxWidth: 920 }}>
                  响应说明：{meta.response}
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {items.map((cap) => {
                  const open = openId === cap.id;
                  return (
                    <Card key={cap.id} style={{ padding: 0, overflow: "hidden" }}>
                      <button
                        onClick={() => setOpenId(open ? null : cap.id)}
                        aria-expanded={open}
                        aria-controls={`capability-${cap.id}`}
                        style={{
                          width: "100%",
                          display: "flex",
                          alignItems: "center",
                          gap: 14,
                          padding: "16px 20px",
                          background: "transparent",
                          border: "none",
                          textAlign: "left",
                          cursor: "pointer",
                        }}
                      >
                        <MethodTag method={cap.method} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="row gap-sm">
                            <span className="heading-md" style={{ fontSize: 16 }}>{cap.name}</span>
                            <Badge tone="muted">{cap.scope}</Badge>
                          </div>
                          <code className="mono text-muted" style={{ fontSize: 13 }}>{cap.path}</code>
                        </div>
                        <IconChevron
                          size={18}
                          style={{
                            color: "var(--muted)",
                            transform: open ? "rotate(90deg)" : "none",
                            transition: "transform 0.2s ease",
                          }}
                        />
                      </button>

                      {open && (
                        <div id={`capability-${cap.id}`} style={{ padding: "0 20px 20px", borderTop: "1px solid var(--hairline)" }}>
                          <p className="body-md" style={{ margin: "16px 0 6px" }}>{cap.description}</p>
                          <p className="body-sm text-muted-soft" style={{ margin: "0 0 16px" }}>
                            响应数据位于 <code className="mono">data</code> 字段；失败时返回标准错误码、错误信息和诊断详情，便于调用方统一处理重试、鉴权失败与参数错误。
                          </p>

                          {cap.params.length > 0 && (
                            <>
                              <div className="caption-upper" style={{ marginBottom: 10 }}>请求参数</div>
                              <div className="table-scroll" style={{ marginBottom: 22 }}>
                              <table className="table">
                                <thead>
                                  <tr>
                                    <th style={{ width: "22%" }}>参数</th>
                                    <th style={{ width: "16%" }}>类型</th>
                                    <th style={{ width: "14%" }}>必填</th>
                                    <th>说明</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {cap.params.map((p) => (
                                    <tr key={p.name}>
                                      <td><code className="mono" style={{ color: "var(--ink)" }}>{p.name}</code></td>
                                      <td><span className="mono text-muted">{p.type}</span></td>
                                      <td>
                                        {p.required ? (
                                          <Badge tone="live">必填</Badge>
                                        ) : (
                                          <span className="text-muted">可选</span>
                                        )}
                                      </td>
                                      <td>{p.description}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                              </div>
                            </>
                          )}

                          <div className="code-examples-grid">
                            <div>
                              <div className="caption-upper" style={{ marginBottom: 10 }}>请求示例</div>
                              <CodeBlock
                                language="bash"
                                code={`curl -X ${cap.method} \\\n  https://open.dml.example.com${samplePath(cap.path)} \\\n  -H "Authorization: Bearer $DML_API_KEY"`}
                              />
                            </div>
                            <div>
                              <div className="caption-upper" style={{ marginBottom: 10 }}>响应示例</div>
                              <CodeBlock language="json" code={cap.sampleResponse} />
                            </div>
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </>
  );
}
