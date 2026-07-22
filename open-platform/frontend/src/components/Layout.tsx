// 应用外壳：侧边栏 + 顶栏 — Supabaze 风格
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { MockUser } from "../types";
import {
  BrandMark,
  IconOverview,
  IconPlay,
  IconUsers,
  IconKey,
  IconCapability,
  IconLogs,
  IconMcp,
  IconQuota,
  IconBook,
} from "./icons";
import "./Layout.css";

export type PageKey = "overview" | "guide" | "users" | "quota" | "keys" | "capabilities" | "debugger" | "logs" | "mcp";

const NAV: {
  key: PageKey;
  label: string;
  description: string;
  icon: ReactNode;
  group: string;
  roles?: MockUser["role"][];
}[] = [
  { key: "overview", label: "运行概览", description: "用量、成功率与配额", icon: <IconOverview />, group: "平台管理" },
  { key: "guide", label: "使用指南", description: "全流程接入与治理", icon: <IconBook />, group: "平台管理" },
  { key: "users", label: "用户权限", description: "分配允许调用的接口", icon: <IconUsers />, group: "平台管理", roles: ["admin"] },
  { key: "quota", label: "用户配额", description: "配置调用与速率上限", icon: <IconQuota />, group: "平台管理", roles: ["admin"] },
  { key: "keys", label: "API 密钥", description: "凭据、环境与权限", icon: <IconKey />, group: "平台管理" },
  { key: "capabilities", label: "开放能力", description: "接口、参数与示例", icon: <IconCapability />, group: "开发者工具" },
  { key: "debugger", label: "API 调试台", description: "构造并发送网关请求", icon: <IconPlay />, group: "开发者工具" },
  { key: "logs", label: "调用日志", description: "审计请求并排查错误", icon: <IconLogs />, group: "开发者工具" },
  { key: "mcp", label: "MCP 接入", description: "连接 AI 客户端", icon: <IconMcp />, group: "开发者工具" },
];

const PAGE_META: Record<PageKey, { title: string; eyebrow: string }> = {
  overview: { title: "运行概览", eyebrow: "平台健康度与使用情况" },
  guide: { title: "使用指南", eyebrow: "从开通、联调到上线治理的完整流程" },
  users: { title: "用户接口权限", eyebrow: "管理每个用户允许调用的开放接口" },
  quota: { title: "用户配额", eyebrow: "为每个普通用户设置调用与速率上限" },
  keys: { title: "API 密钥", eyebrow: "安全管理外部访问凭据" },
  capabilities: { title: "开放能力目录", eyebrow: "查找可调用接口与请求示例" },
  debugger: { title: "API 调试台", eyebrow: "通过开放平台网关验证请求参数与响应" },
  logs: { title: "调用日志", eyebrow: "审计请求并定位异常" },
  mcp: { title: "MCP 接入指南", eyebrow: "将 DML 能力连接到 AI 客户端" },
};

export function Layout({
  page,
  onNavigate,
  children,
  user,
  users,
  onUserChange,
  onLogout,
}: {
  page: PageKey;
  onNavigate: (p: PageKey) => void;
  children: ReactNode;
  user: MockUser;
  users: MockUser[];
  onUserChange: (user: MockUser) => void;
  onLogout: () => void;
}) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const visibleNav = NAV.filter((item) => !item.roles || item.roles.includes(user.role));

  useEffect(() => {
    const closeMenu = (event: MouseEvent) => {
      if (!userMenuRef.current?.contains(event.target as Node)) setUserMenuOpen(false);
    };
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, []);

  let lastGroup = "";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        {/* 品牌区 */}
        <div className="brand">
          <BrandMark size={24} />
          <div>
            <div className="brand-name">DML 开放平台</div>
            <div className="brand-sub">Open Platform</div>
          </div>
        </div>

        {/* 导航 */}
        <nav className="nav">
          {visibleNav.map((item) => {
            const showGroup = item.group !== lastGroup;
            lastGroup = item.group;
            return (
              <div key={item.key}>
                {showGroup && <div className="nav-section">{item.group}</div>}
                <button
                  className={`nav-item${page === item.key ? " active" : ""}`}
                  onClick={() => onNavigate(item.key)}
                  aria-current={page === item.key ? "page" : undefined}
                  title={`${item.label}：${item.description}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-copy">
                    <span className="nav-label">{item.label}</span>
                    <span className="nav-description">{item.description}</span>
                  </span>
                </button>
              </div>
            );
          })}
        </nav>

        {/* 本地身份切换 */}
        <div className="user-switcher" ref={userMenuRef}>
          {userMenuOpen && (
            <div className="user-menu" role="menu" aria-label="切换本地身份">
              <div className="user-menu-head">本地身份切换</div>
              {(user.role === "admin" ? users : [user]).map((item) => (
                <button
                  key={item.id}
                  role="menuitemradio"
                  aria-checked={item.id === user.id}
                  className={`user-option${item.id === user.id ? " active" : ""}`}
                  onClick={() => {
                    onUserChange(item);
                    setUserMenuOpen(false);
                  }}
                >
                  <span className="avatar avatar-sm">{item.avatar}</span>
                  <span className="user-option-copy">
                    <strong>{item.name}</strong>
                    <span>{item.role === "admin" ? "平台管理员 · 全量视图" : "普通用户 · 个人视图"}</span>
                  </span>
                  {item.id === user.id && <span className="user-current">当前</span>}
                </button>
              ))}
              <button className="user-option" onClick={onLogout}>
                <span className="avatar avatar-sm">退</span>
                <span className="user-option-copy"><strong>退出登录</strong><span>返回控制台登录页</span></span>
              </button>
              <div className="user-menu-note">管理员可切换控制台视角；普通用户仅查看个人视图。</div>
            </div>
          )}
          <button
            className="sidebar-foot"
            onClick={() => setUserMenuOpen((open) => !open)}
            aria-haspopup="menu"
            aria-expanded={userMenuOpen}
          >
            <div className="avatar">{user.avatar}</div>
            <div className="sidebar-user-copy">
              <div className="body-sm sidebar-user-name">{user.name}</div>
              <div className="caption text-muted">{user.role === "admin" ? "平台管理员" : "普通用户"} · 网关</div>
            </div>
            <span className="user-switch-arrow">⌃</span>
          </button>
        </div>
      </aside>

      {/* 主内容区 */}
      <div className="main">
        <header className="topbar">
          <div>
            <div className="topbar-title">{PAGE_META[page].title}</div>
            <div className="topbar-eyebrow">{PAGE_META[page].eyebrow}</div>
          </div>
          <div className="env-pill" aria-label="当前环境：生产环境，服务运行正常">
            <span className="badge-dot" style={{ background: "var(--success)" }} />
            <span>生产环境</span>
            <span className="env-state">运行正常</span>
          </div>
        </header>
        <main className="content fade-up" key={page}>
          {children}
        </main>
      </div>
    </div>
  );
}
