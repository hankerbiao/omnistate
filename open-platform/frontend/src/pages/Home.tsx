import { useEffect, useRef, useState } from "react";
import { Button, useToast } from "../components/ui";
import { api } from "../services/api";
import type { MockUser } from "../types";
import { IconCapability, IconKey, IconLogs } from "../components/icons";
import "./Home.css";

const PILLARS = [
  {
    title: "统一开放能力",
    detail: "把测试任务、执行状态、时间线和平台数据能力沉淀为标准接口。",
    icon: <IconCapability size={18} />,
  },
  {
    title: "安全接入凭据",
    detail: "通过 API 密钥和权限范围控制外部系统访问边界。",
    icon: <IconKey size={18} />,
  },
  {
    title: "可观测调用链路",
    detail: "从概览到调用日志，持续追踪接口成功率、耗时与异常请求。",
    icon: <IconLogs size={18} />,
  },
];

const METRICS = [
  { value: "API", label: "标准化网关接入" },
  { value: "MCP", label: "面向 AI 客户端扩展" },
  { value: "Audit", label: "调用审计与排障" },
];

export function Home({
  user,
  onEnter,
  onLogin,
}: {
  user: MockUser | null;
  onEnter: () => void;
  onLogin: (user: MockUser) => void;
}) {
  const { push } = useToast();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (user) {
      onEnter();
      return;
    }
    if (!username.trim() || !password) {
      push("请输入用户名和密码", "error");
      return;
    }
    setBusy(true);
    try {
      const result = await api.login(username.trim(), password);
      api.setConsoleUserId(result.user.id);
      onLogin(result.user);
      push("登录成功", "success");
    } catch (error) {
      push(error instanceof Error ? error.message : "用户名或密码错误", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="home-shell">
      <DataScene />
      <header className="home-nav" aria-label="首页导航">
        <div className="home-brand">
          <DmlLogo />
          <span>DML 开发平台</span>
        </div>
        {user ? (
          <button className="home-nav-action" onClick={onEnter}>
            进入管理页面
          </button>
        ) : (
          <button className="home-nav-action" form="home-login-form" type="submit" disabled={busy}>
            登录管理页面
          </button>
        )}
      </header>

      <main className="home-main">
        <section className="home-hero">
          <div className="home-hero-copy">
            <div className="home-kicker">DML Developer Platform</div>
            <h1>DML 开发平台</h1>
            <p>
              面向研发、测试与 AI Agent 的统一开放能力入口。以更清晰的接口、更可控的凭据和更完整的调用审计，连接 DML 核心能力与业务系统。
            </p>
          </div>

          <form id="home-login-form" className="home-login-card" onSubmit={submit}>
            <div>
              <div className="home-form-kicker">{user ? "Console Ready" : "Management Console"}</div>
              <h2>{user ? `欢迎回来，${user.name}` : "登录管理页面"}</h2>
              <p>{user ? "当前身份已验证，可直接进入开放平台控制台。" : "使用平台账号进入能力、密钥、调试与日志管理。"}</p>
            </div>

            {user ? (
              <div className="home-ready-panel">
                <strong>Gateway Ready</strong>
                <span>开放能力网关已就绪</span>
              </div>
            ) : (
              <>
                <div className="field">
                  <label className="field-label" htmlFor="home-login-username">用户名</label>
                  <input
                    id="home-login-username"
                    className="input"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                  />
                </div>
                <div className="field">
                  <label className="field-label" htmlFor="home-login-password">密码</label>
                  <input
                    id="home-login-password"
                    className="input"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                  />
                </div>
                <Button type="submit" disabled={busy}>{busy ? "登录中..." : "登录管理页面"}</Button>
                <span className="home-login-hint">默认管理员账号 admin / admin123</span>
              </>
            )}
          </form>
        </section>

        <section className="home-overview" aria-label="平台能力概览">
          <div className="home-metrics">
            {METRICS.map((item) => (
              <div className="home-metric" key={item.value}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
          <div className="home-pillars">
            {PILLARS.map((item) => (
              <article className="home-pillar" key={item.title}>
                <div className="home-pillar-icon">{item.icon}</div>
                <h2>{item.title}</h2>
                <p>{item.detail}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function DmlLogo() {
  return (
    <svg className="home-logo" viewBox="0 0 40 40" role="img" aria-label="DML logo">
      <rect className="home-logo-bg" x="2" y="2" width="36" height="36" rx="10" />
      <path className="home-logo-path" d="M11 27V13h6.2c4.1 0 6.8 2.8 6.8 7s-2.7 7-6.8 7H11Z" />
      <path className="home-logo-line" d="M18 13l5.2 14M23.2 27 29 13v14" />
    </svg>
  );
}

function DataScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const context = canvas.getContext("2d");
    if (!context) return undefined;

    let frame = 0;
    let animation = 0;
    let width = 0;
    let height = 0;
    const nodes = Array.from({ length: 38 }, (_, index) => ({
      x: (index * 137) % 1200,
      y: (index * 251) % 760,
      radius: 1.2 + (index % 4) * 0.35,
      speed: 0.18 + (index % 5) * 0.025,
      phase: index * 0.62,
    }));

    const resize = () => {
      const ratio = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const draw = () => {
      frame += 0.008;
      context.clearRect(0, 0, width, height);
      context.fillStyle = "#f7faf8";
      context.fillRect(0, 0, width, height);

      context.strokeStyle = "rgba(23, 23, 23, 0.035)";
      context.lineWidth = 1;
      for (let x = 0; x < width; x += 56) {
        context.beginPath();
        context.moveTo(x, 0);
        context.lineTo(x, height);
        context.stroke();
      }
      for (let y = 0; y < height; y += 56) {
        context.beginPath();
        context.moveTo(0, y);
        context.lineTo(width, y);
        context.stroke();
      }

      const placed = nodes.map((node) => ({
        x: ((node.x / 1200) * width + Math.sin(frame + node.phase) * 28 + width) % width,
        y: ((node.y / 760) * height + Math.cos(frame * 0.8 + node.phase) * 22 + height) % height,
        radius: node.radius,
        speed: node.speed,
      }));

      for (let i = 0; i < placed.length; i += 1) {
        for (let j = i + 1; j < placed.length; j += 1) {
          const a = placed[i];
          const b = placed[j];
          const distance = Math.hypot(a.x - b.x, a.y - b.y);
          if (distance < 150) {
            context.strokeStyle = `rgba(36, 180, 126, ${0.18 - distance / 1100})`;
            context.lineWidth = 1;
            context.beginPath();
            context.moveTo(a.x, a.y);
            context.lineTo(b.x, b.y);
            context.stroke();
          }
        }
      }

      placed.forEach((node) => {
        context.beginPath();
        context.fillStyle = "rgba(36, 180, 126, 0.58)";
        context.arc(node.x, node.y, node.radius + Math.sin(frame * 10 * node.speed) * 0.35, 0, Math.PI * 2);
        context.fill();
      });

      animation = window.requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener("resize", resize);

    return () => {
      window.cancelAnimationFrame(animation);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="home-scene" aria-hidden="true" />;
}
