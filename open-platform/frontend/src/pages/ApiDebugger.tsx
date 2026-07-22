import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import type { ApiKey, Capability, DebugResponse, MockUser } from "../types";
import { Badge, Button, Card, CodeBlock, Loading, MethodTag, useToast } from "../components/ui";
import { IconPlay } from "../components/icons";

export function ApiDebugger({ user }: { user: MockUser }) {
  const { push } = useToast();
  const [capabilities, setCapabilities] = useState<Capability[] | null>(null);
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [capabilityId, setCapabilityId] = useState("");
  const [keyId, setKeyId] = useState("");
  const [env, setEnv] = useState<"live" | "test">("test");
  const [params, setParams] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<DebugResponse | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.getMyCapabilities(), api.listKeys()]).then(([capabilityResult, apiKeys]) => {
      const visibleKeys = user.role === "admin" ? apiKeys : apiKeys.filter((key) => key.name === "数据看板同步" || key.name === "本地联调（测试）");
      const visibleCapabilities = capabilityResult.capabilities;
      setCapabilities(visibleCapabilities);
      setKeys(visibleKeys.filter((key) => key.status === "active"));
      setCapabilityId(visibleCapabilities[0]?.id ?? "");
      setKeyId(apiKeys.find((key) => key.status === "active" && key.env === "test")?.id ?? apiKeys[0]?.id ?? "");
    });
  }, [user.id, user.allowedCapabilityIds]);

  const capability = useMemo(() => capabilities?.find((item) => item.id === capabilityId) ?? null, [capabilities, capabilityId]);
  const availableKeys = useMemo(() => keys?.filter((key) => key.env === env) ?? [], [keys, env]);

  useEffect(() => {
    if (!capability) return;
    setParams(Object.fromEntries(capability.params.map((param) => [param.name, param.name === "task_id" ? "ET-2026-000128" : param.name === "limit" ? "20" : ""])));
    setResponse(null);
  }, [capability]);

  useEffect(() => {
    if (!availableKeys.some((key) => key.id === keyId)) setKeyId(availableKeys[0]?.id ?? "");
  }, [availableKeys, keyId]);

  useEffect(() => {
    if (!capability || !keys) return;
    const currentKey = keys.find((key) => key.id === keyId);
    if (currentKey?.env === env && currentKey.scopes.includes(capability.scope)) return;

    const compatibleInCurrentEnv = keys.find(
      (key) => key.status === "active" && key.env === env && key.scopes.includes(capability.scope),
    );
    if (compatibleInCurrentEnv) {
      setKeyId(compatibleInCurrentEnv.id);
      return;
    }

    const compatibleKey = keys.find((key) => key.status === "active" && key.scopes.includes(capability.scope));
    if (compatibleKey) {
      setEnv(compatibleKey.env);
      setKeyId(compatibleKey.id);
    }
  }, [capability, env, keyId, keys]);

  if (!capabilities || !keys || !capability) return <Loading label="正在准备 API 调试台" />;

  const selectedKey = keys.find((key) => key.id === keyId);
  const scopeReady = selectedKey?.scopes.includes(capability.scope) ?? false;
  const requestBody = capability.method === "GET" ? "" : JSON.stringify(params, null, 2);
  const curlPreview = `curl -X ${capability.method} \\\n  https://${env === "live" ? "open" : "sandbox"}.dml.example.com${capability.path} \\\n  -H "Authorization: Bearer ${selectedKey?.masked ?? "请选择密钥"}"${requestBody ? ` \\\n  -H "Content-Type: application/json" \\\n  -d '${requestBody}'` : ""}`;

  const send = async () => {
    const missing = capability.params.find((param) => param.required && !params[param.name]?.trim());
    if (missing) {
      push(`请填写必填参数：${missing.name}`, "error");
      return;
    }
    if (!keyId) {
      push(`当前${env === "live" ? "生产" : "测试"}环境没有可用密钥`, "error");
      return;
    }
    if (!scopeReady) {
      push(`所选密钥缺少 ${capability.scope} 权限`, "error");
      return;
    }
    setBusy(true);
    setResponse(null);
    try {
      const result = await api.debugRequest({ capabilityId, keyId, env, params });
      setResponse(result);
      push(result.statusCode < 400 ? "网关请求成功" : "网关请求返回错误", result.statusCode < 400 ? "success" : "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head">
        <h1 className="display-md">API 在线调试台</h1>
        <p>选择开放能力和测试密钥，填写请求参数并通过开放平台网关发送调试请求。</p>
      </div>

      <div className="debugger-layout">
        <Card>
          <div className="row between" style={{ marginBottom: 20 }}>
            <h2 className="heading-md">构造请求</h2>
            <Badge tone="success">网关联调</Badge>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="debug-capability">开放能力</label>
            <select id="debug-capability" className="input" value={capabilityId} onChange={(event) => setCapabilityId(event.target.value)}>
              {capabilities.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.method}</option>)}
            </select>
          </div>
          <div className="debug-method-line">
            <MethodTag method={capability.method} />
            <code className="mono">{capability.path}</code>
          </div>
          <p className="body-sm text-muted" style={{ margin: "10px 0 20px" }}>{capability.summary}</p>

          <div className="field">
            <label className="field-label">请求环境</label>
            <div className="segmented">
              <button aria-pressed={env === "test"} className={env === "test" ? "active" : ""} onClick={() => setEnv("test")}>测试环境</button>
              <button aria-pressed={env === "live"} className={env === "live" ? "active" : ""} onClick={() => setEnv("live")}>生产环境</button>
            </div>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="debug-key">API 密钥</label>
            <select id="debug-key" className="input" value={keyId} onChange={(event) => setKeyId(event.target.value)}>
              {availableKeys.length === 0 && <option value="">当前环境没有可用密钥</option>}
              {availableKeys.map((key) => <option key={key.id} value={key.id}>{key.name} · {key.masked}</option>)}
            </select>
            <span className={`field-hint ${scopeReady ? "text-success" : "text-danger"}`}>
              {scopeReady
                ? `权限检查通过：${capability.scope}`
                : `所选${env === "live" ? "生产" : "测试"}密钥需要 ${capability.scope} 权限`}
            </span>
          </div>

          {capability.params.map((param) => (
            <div className="field" key={param.name}>
              <label className="field-label" htmlFor={`debug-${param.name}`}>{param.name}{param.required ? " *" : ""}</label>
              <input id={`debug-${param.name}`} className="input mono" value={params[param.name] ?? ""} onChange={(event) => setParams((current) => ({ ...current, [param.name]: event.target.value }))} placeholder={param.description} />
              <span className="field-hint">{param.type} · {param.description}</span>
            </div>
          ))}
          <Button onClick={send} disabled={busy || !scopeReady || !keyId}>
            <IconPlay />
            {busy ? "正在发送请求…" : "发送网关请求"}
          </Button>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <h2 className="heading-md" style={{ marginBottom: 14 }}>请求预览</h2>
            <CodeBlock language="bash" code={curlPreview} />
          </Card>
          <Card>
            <div className="row between" style={{ marginBottom: 14 }}>
              <h2 className="heading-md">网关响应</h2>
              {response && <Badge tone={response.statusCode < 400 ? "success" : "error"} dot>HTTP {response.statusCode}</Badge>}
            </div>
            {!response ? (
              <div className="response-placeholder">
                <span>发送请求后，将在这里显示 Request ID、响应耗时和 JSON 数据。</span>
              </div>
            ) : (
              <>
                <div className="response-meta">
                  <div><span>Request ID</span><code>{response.requestId}</code></div>
                  <div><span>耗时</span><strong>{response.latencyMs} ms</strong></div>
                  <div><span>请求地址</span><code>{response.requestUrl}</code></div>
                </div>
                <CodeBlock language="json" code={response.responseBody} />
              </>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
