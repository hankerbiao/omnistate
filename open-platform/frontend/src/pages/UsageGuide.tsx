// 使用指南页：覆盖开放平台从申请到治理的完整使用周期
import { Badge, Card, CodeBlock } from "../components/ui";
import { IconBook, IconCheck, IconKey, IconMcp, IconPlay } from "../components/icons";
import "./UsageGuide.css";

const LIFECYCLE = [
  {
    phase: "01",
    title: "账号与角色准备",
    owner: "管理员",
    summary: "创建平台用户，确认是否需要管理员视图，并为普通用户分配可访问的开放能力。",
    steps: ["进入用户权限页新增或选择用户", "勾选允许调用的接口能力", "通知用户首次登录并完成密码修改"],
  },
  {
    phase: "02",
    title: "能力选型与联调",
    owner: "开发者",
    summary: "从开放能力目录确认接口用途、请求方法、参数结构和响应格式，再用调试台验证样例请求。",
    steps: ["在开放能力页筛选接口", "复制接口路径与参数示例", "在 API 调试台发送测试请求"],
  },
  {
    phase: "03",
    title: "密钥创建与环境隔离",
    owner: "开发者",
    summary: "为测试、预发和生产分别创建密钥，密钥只授予当前应用真实需要的能力范围。",
    steps: ["进入 API 密钥页创建密钥", "选择允许渠道与权限范围", "复制密钥后存入服务端密钥管理系统"],
  },
  {
    phase: "04",
    title: "业务系统集成",
    owner: "开发者",
    summary: "在业务服务中通过开放平台网关调用 DML 能力，统一携带 Bearer Token 并处理标准响应 envelope。",
    steps: ["配置网关 base URL", "请求头加入 Authorization", "按 code/message/data 结构处理成功与失败"],
  },
  {
    phase: "05",
    title: "上线观察与审计",
    owner: "管理员 / 开发者",
    summary: "上线后通过运行概览与调用日志追踪成功率、延迟、限流、异常详情和密钥使用情况。",
    steps: ["观察今日调用量与成功率趋势", "在调用日志页按状态码定位异常", "按日志详情复现并修正请求"],
  },
];

const CHECKLIST = [
  "普通用户只能看到个人视图；管理员可以切换用户视角。",
  "密钥只展示一次，创建后立即保存到安全位置。",
  "生产密钥不要放在前端代码、移动端包或公开仓库中。",
  "接口返回非 0 code 时，以 message 和 data.detail 作为排查入口。",
  "上线后持续关注失败率、响应耗时和异常请求详情。",
];

const ROLE_GUIDES = [
  {
    role: "平台管理员",
    pages: "用户权限、运行概览、调用日志",
    goal: "控制谁能用，并确认平台是否健康运行。",
  },
  {
    role: "业务开发者",
    pages: "开放能力、API 密钥、API 调试台、MCP 接入",
    goal: "找到接口、完成联调、把能力接入业务系统或 AI 客户端。",
  },
  {
    role: "排障人员",
    pages: "运行概览、调用日志、API 调试台",
    goal: "复现失败请求，定位权限、参数、限流或后端异常。",
  },
];

export function UsageGuide() {
  return (
    <>
      <div className="page-head guide-head">
        <div>
          <div className="row gap-sm" style={{ marginBottom: 8 }}>
            <IconBook size={22} style={{ color: "var(--primary-deep)" }} />
            <Badge tone="live">全流程周期</Badge>
          </div>
          <h1 className="display-md">DML 开放平台使用指南</h1>
          <p>
            从账号开通、权限分配，到开发联调、业务集成、上线监控和 MCP 接入，按这套流程可以完成一次完整的开放能力接入。
          </p>
        </div>
        <div className="guide-summary" aria-label="推荐使用顺序">
          <span>推荐顺序</span>
          <strong>权限 → 能力 → 密钥 → 调试 → 上线 → 审计</strong>
        </div>
      </div>

      <section className="guide-section">
        <div className="guide-section-title">
          <span className="caption-upper">Lifecycle</span>
          <h2 className="heading-lg">完整使用周期</h2>
        </div>
        <div className="guide-timeline">
          {LIFECYCLE.map((item) => (
            <Card key={item.phase}>
              <div className="guide-step-head">
                <span className="guide-step-no">{item.phase}</span>
                <Badge tone={item.owner === "开发者" ? "test" : "muted"}>{item.owner}</Badge>
              </div>
              <h3 className="heading-md">{item.title}</h3>
              <p>{item.summary}</p>
              <ul className="guide-list">
                {item.steps.map((step) => (
                  <li key={step}>
                    <IconCheck size={15} />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </section>

      <section className="guide-section">
        <div className="guide-section-title">
          <span className="caption-upper">Integration</span>
          <h2 className="heading-lg">标准接入方式</h2>
        </div>
        <div className="guide-grid two">
          <Card>
            <div className="guide-card-kicker">
              <IconKey size={18} />
              <span>HTTP API</span>
            </div>
            <p className="body-sm text-muted">
              后端服务通过开放平台网关调用能力。所有请求统一使用 Bearer Token，响应采用 code/message/data 结构。
            </p>
            <CodeBlock
              language="bash"
              code={`curl -X POST https://open.dml.example.com/api/v1/gateway/run \\
  -H "Authorization: Bearer dml_live_xxxxxxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"capabilityId":"test_task_status","input":{"taskId":"TASK-10001"}}'`}
            />
          </Card>
          <Card>
            <div className="guide-card-kicker">
              <IconMcp size={18} />
              <span>MCP 客户端</span>
            </div>
            <p className="body-sm text-muted">
              AI 客户端通过 MCP 服务读取任务状态、时间线和其他只读能力。密钥权限决定客户端可访问的工具范围。
            </p>
            <CodeBlock
              language="json"
              code={`{
  "mcpServers": {
    "dml-open-platform": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "env": {
        "DML_MCP_BACKEND_TOKEN": "dml_live_xxxxxxxx"
      }
    }
  }
}`}
            />
          </Card>
        </div>
      </section>

      <section className="guide-section">
        <div className="guide-section-title">
          <span className="caption-upper">Operation</span>
          <h2 className="heading-lg">角色分工与验收清单</h2>
        </div>
        <div className="guide-grid two">
          <Card>
            <div className="guide-role-list">
              {ROLE_GUIDES.map((item) => (
                <div className="guide-role" key={item.role}>
                  <div>
                    <strong>{item.role}</strong>
                    <span>{item.pages}</span>
                  </div>
                  <p>{item.goal}</p>
                </div>
              ))}
            </div>
          </Card>
          <Card variant="dark">
            <div className="guide-card-kicker dark">
              <IconPlay size={18} />
              <span>上线前确认</span>
            </div>
            <ul className="guide-list dark">
              {CHECKLIST.map((item) => (
                <li key={item}>
                  <IconCheck size={15} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </section>
    </>
  );
}
