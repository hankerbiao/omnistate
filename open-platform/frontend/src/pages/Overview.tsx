// 概览页 — Supabaze 风格
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { MockUser, OverviewStats } from "../types";
import { Card, Loading } from "../components/ui";
import { IconArrowUp, IconArrowDown, IconKey } from "../components/icons";
import { formatNumber } from "../utils";

function TrendPill({ value, suffix = "%" }: { value: number; suffix?: string }) {
  const up = value >= 0;
  return (
    <span className={`stat-trend ${up ? "trend-up" : "trend-down"}`}>
      {up ? <IconArrowUp /> : <IconArrowDown />}
      {Math.abs(value)}
      {suffix} 较昨日
    </span>
  );
}

/* 近 7 日调用量柱状图（纯 SVG）— Supabaze 配色 */
function DailyChart({ data }: { data: OverviewStats["daily"] }) {
  const W = 640;
  const H = 200;
  const padL = 8;
  const padB = 28;
  const max = Math.max(...data.map((d) => d.calls)) * 1.15;
  const barW = 40;
  const gap = (W - padL * 2 - barW * data.length) / (data.length - 1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="200" role="img" aria-label="近七日调用量">
      {/* 网格线 */}
      {[0.25, 0.5, 0.75, 1].map((r) => (
        <line
          key={r}
          x1={padL}
          x2={W - padL}
          y1={(H - padB) * (1 - r)}
          y2={(H - padB) * (1 - r)}
          stroke="var(--hairline-cool)"
          strokeWidth={1}
        />
      ))}
      {data.map((d, i) => {
        const x = padL + i * (barW + gap);
        const h = ((H - padB) * d.calls) / max;
        const y = H - padB - h;
        const isLast = i === data.length - 1;
        return (
          <g key={d.date}>
            <rect
              x={x}
              y={y}
              width={barW}
              height={h}
              rx={4}
              fill={isLast ? "var(--primary)" : "var(--hairline-cool-3)"}
            />
            <text
              x={x + barW / 2}
              y={y - 6}
              textAnchor="middle"
              fontSize={11}
              fontWeight={500}
              fill={isLast ? "var(--primary)" : "var(--muted)"}
              fontFamily="var(--font-sans)"
            >
              {formatNumber(d.calls)}
            </text>
            <text
              x={x + barW / 2}
              y={H - 8}
              textAnchor="middle"
              fontSize={12}
              fill="var(--muted)"
              fontFamily="var(--font-sans)"
            >
              {d.date}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CapabilityBars({ data }: { data: OverviewStats["topCapabilities"] }) {
  const max = Math.max(...data.map((d) => d.calls));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {data.map((d) => (
        <div key={d.name}>
          <div className="row between" style={{ marginBottom: 6 }}>
            <span className="body-sm" style={{ color: "var(--ink)" }}>{d.name}</span>
            <span className="caption">{formatNumber(d.calls)}</span>
          </div>
          <div style={{ height: 6, background: "var(--canvas-soft)", borderRadius: 99 }}>
            <div
              style={{
                width: `${(d.calls / max) * 100}%`,
                height: "100%",
                background: "var(--primary)",
                borderRadius: 99,
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Overview({ user }: { user: MockUser }) {
  const [stats, setStats] = useState<OverviewStats | null>(null);

  useEffect(() => {
    api.getOverview().then(setStats);
  }, []);

  if (!stats) return <Loading />;

  const quotaPct = Math.round((stats.quotaUsed / stats.quotaLimit) * 100);

  return (
    <>
      {/* 页面头部 */}
      <div className="page-head">
        <div className="row gap-sm" style={{ marginBottom: 4 }}>
          <h1 className="display-md">欢迎回来，{user.name}</h1>
          <span className={`role-badge role-${user.role}`}>{user.role === "admin" ? "管理员视图" : "个人视图"}</span>
        </div>
        <p>
          {user.role === "admin"
            ? "集中查看全平台健康度、所有应用调用趋势、配额风险和密钥安全情况。"
            : "查看你所属应用的调用趋势、可用密钥与配额使用情况；平台级治理数据仅管理员可见。"}
        </p>
      </div>

      {/* 统计卡 — 4 列网格 */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="caption-upper">今日调用量</span>
          <span className="stat-value">{formatNumber(stats.totalCallsToday)}</span>
          <TrendPill value={stats.totalCallsTrend} />
        </div>
        <div className="stat-card">
          <span className="caption-upper">成功率</span>
          <span className="stat-value">{stats.successRate}%</span>
          <TrendPill value={stats.successRateTrend} />
        </div>
        <div className="stat-card">
          <span className="caption-upper">活跃密钥</span>
          <span className="stat-value">{stats.activeKeys}</span>
          <span className="caption text-muted">
            <IconKey size={12} style={{ marginRight: 4, color: "var(--muted)" }} />
            正在使用中
          </span>
        </div>
        <div className="stat-card">
          <span className="caption-upper">月度配额</span>
          <span className="stat-value">{quotaPct}%</span>
          <div style={{ height: 4, background: "var(--canvas-soft)", borderRadius: 99 }}>
            <div
              style={{
                width: `${quotaPct}%`,
                height: "100%",
                background: "var(--primary)",
                borderRadius: 99,
                transition: "width 0.3s ease",
              }}
            />
          </div>
          <span className="caption text-muted">
            {formatNumber(stats.quotaUsed)} / {formatNumber(stats.quotaLimit)} 次
          </span>
        </div>
      </div>

      <div className="insight-grid">
        <div className="insight-card insight-warning">
          <div>
            <span className="caption-upper">配额预警</span>
            <h3>{user.role === "admin" ? "质量数据看板已使用 89% 月度配额" : "你所属的质量数据看板已使用 89% 配额"}</h3>
            <p>按当前调用速度预计 4 天后耗尽，建议降低轮询频率或申请扩容。</p>
          </div>
          <span className="insight-value">89%</span>
        </div>
        {user.role === "admin" ? (
          <div className="insight-card">
            <div>
              <span className="caption-upper">运行质量</span>
              <h3>最近请求成功率保持在 98.6%</h3>
              <p>当前没有大面积异常，可重点关注 429 限流请求和高延迟接口。</p>
            </div>
            <span className="insight-value">98.6%</span>
          </div>
        ) : (
          <div className="insight-card">
            <div>
              <span className="caption-upper">我的接入状态</span>
              <h3>测试环境配置已完成</h3>
              <p>当前账号可使用 3 项只读能力，生产权限需要管理员审批。</p>
            </div>
            <span className="insight-value">3</span>
          </div>
        )}
      </div>

      {/* 图表区 — 1.6:1 比例 */}
      <div className="dashboard-grid">
        <Card>
          <div className="row between" style={{ marginBottom: 16 }}>
            <h3 className="heading-md">近 7 日调用趋势</h3>
            <span className="caption text-muted">单位：次</span>
          </div>
          <DailyChart data={stats.daily} />
        </Card>
        <Card>
          <h3 className="heading-md" style={{ marginBottom: 16 }}>
            热门开放能力
          </h3>
          <CapabilityBars data={stats.topCapabilities} />
        </Card>
      </div>
    </>
  );
}
