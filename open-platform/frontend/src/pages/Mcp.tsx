// MCP 接入指南页
import { Card, CodeBlock, Badge } from "../components/ui";
import { IconMcp, IconCheck } from "../components/icons";

const TOOLS = [
  { name: "list_my_open_capabilities", desc: "列出当前 API Key 可访问的开放能力和参数说明" },
  { name: "list_my_test_tasks", desc: "查询当前令牌所属用户最近创建的自动化执行任务" },
  { name: "list_test_cases", desc: "查询测试用例列表，支持按项目、状态和数量过滤" },
  { name: "get_test_task_status", desc: "查询单个自动化执行任务的整体状态与执行进度" },
  { name: "get_test_task_timeline", desc: "查询自动化执行任务的业务轨迹与执行事件时间线" },
  { name: "get_execution_report", desc: "读取自动化执行任务的执行报告与失败分析摘要" },
];

export function Mcp() {
  return (
    <>
      <div className="page-head">
        <h1 className="display-md">MCP 接入指南</h1>
        <p>
          按照以下 3 个步骤，将开放平台只读能力接入支持 Model Context Protocol（MCP）的 AI 客户端。接入后，客户端可在 API 密钥权限范围内读取任务、报告和测试用例数据。
        </p>
      </div>

      {/* 步骤 1 */}
      <Card style={{ marginBottom: 20 }}>
        <div className="row gap-sm" style={{ marginBottom: 14 }}>
          <StepDot n={1} />
          <h3 className="title-md">准备 API 密钥</h3>
        </div>
        <p className="body-md" style={{ marginBottom: 0 }}>
          在「API 密钥」页面创建一个允许 MCP 渠道、并带
          <code className="mono" style={{ marginLeft: 4 }}>execution_tasks:read</code>
          <span style={{ margin: "0 4px" }}>和</span>
          <code className="mono">test_cases:read</code> 权限的密钥，作为 MCP 服务访问后端的凭据。
        </p>
      </Card>

      {/* 步骤 2 */}
      <Card style={{ marginBottom: 20 }}>
        <div className="row gap-sm" style={{ marginBottom: 14 }}>
          <StepDot n={2} />
          <h3 className="title-md">启动 MCP 服务</h3>
        </div>
        <p className="body-md">在部署 MCP 服务的机器上执行：</p>
        <CodeBlock
          language="bash"
          code={`cd open-platform/backend
uv sync --extra dev

export DML_MCP_TRANSPORT="streamable-http"
export DML_MCP_API_KEY="dml_live_xxxxxxxx"          # 你的 API 密钥
export DML_GATEWAY_UPSTREAMS="https://dml.example.com"

uv run python -m mcp_server.server`}
        />
      </Card>

      {/* 步骤 3 */}
      <Card style={{ marginBottom: 20 }}>
        <div className="row gap-sm" style={{ marginBottom: 14 }}>
          <StepDot n={3} />
          <h3 className="title-md">在客户端中配置</h3>
        </div>
        <p className="body-md">
          以 Claude Desktop / Cursor 为例，在 MCP 配置文件中加入：
        </p>
        <CodeBlock
          language="json"
          code={`{
  "mcpServers": {
    "dml-open-platform": {
      "type": "streamable-http",
      "url": "http://10.2.48.65:8810/mcp",
      "headers": {
        "Authorization": "Bearer dml_live_xxxxxxxx"
      }
    }
  }
}`}
        />
      </Card>

      {/* 可用工具 */}
      <Card variant="dark">
        <div className="row gap-sm" style={{ marginBottom: 18 }}>
          <IconMcp size={20} style={{ color: "var(--primary)" }} />
          <h3 className="title-md" style={{ color: "var(--canvas)" }}>可用 MCP 工具</h3>
          <Badge tone="test">只读</Badge>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {TOOLS.map((t) => (
            <div key={t.name} className="row gap-sm" style={{ alignItems: "flex-start" }}>
              <IconCheck size={16} style={{ color: "var(--primary)", marginTop: 3 }} />
              <div>
                <code className="mono" style={{ color: "var(--canvas)", fontSize: 14 }}>{t.name}</code>
                <div className="body-sm" style={{ color: "#c8c8c8" }}>{t.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function StepDot({ n }: { n: number }) {
  return (
    <span
      style={{
        width: 28,
        height: 28,
        borderRadius: "50%",
        background: "var(--primary)",
        color: "var(--on-primary)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 14,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      {n}
    </span>
  );
}
