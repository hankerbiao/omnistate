import { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { AutomationTestCaseResponse, TestCaseResponse } from '../../types';
import type { UnifiedCaseItem } from './testCaseBoardTypes';
import { AUTO_STATUS_DOT, MANUAL_STATUS_DOT, AUTO_STATUS_LABELS } from './testCaseBoardTypes';
import { boardStyles as S } from './testCaseBoardStyles';

interface TestCaseBoardStatsProps {
  autoCases: AutomationTestCaseResponse[];
  manualCases: TestCaseResponse[];
  unifiedList: UnifiedCaseItem[];
  loading: boolean;
}

const CHART_COLORS = ['#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4'];
const RADIAN = Math.PI / 180;

function renderPieLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }: {
  cx?: number; cy?: number; midAngle?: number; innerRadius?: number; outerRadius?: number; percent?: number;
}) {
  const radius = (innerRadius ?? 0) + ((outerRadius ?? 0) - (innerRadius ?? 0)) * 0.5;
  const x = (cx ?? 0) + radius * Math.cos(-(midAngle ?? 0) * RADIAN);
  const y = (cy ?? 0) + radius * Math.sin(-(midAngle ?? 0) * RADIAN);
  return (percent ?? 0) > 0.06 ? (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${((percent ?? 0) * 100).toFixed(0)}%`}
    </text>
  ) : null;
}

function countByKey<T>(items: T[], keyFn: (item: T) => string): { name: string; value: number }[] {
  const map = items.reduce<Record<string, number>>((acc, item) => {
    const key = keyFn(item) || '未设置';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(map)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

const TestCaseBoardStats: React.FC<TestCaseBoardStatsProps> = ({ autoCases, manualCases, unifiedList, loading }) => {

  /* ── Computed ── */
  const stats = useMemo(() => {
    const total = unifiedList.length;
    const autoCount = autoCases.length;
    const manualCount = manualCases.length;
    const activeAuto = autoCases.filter(c => c.status === 'ACTIVE').length;
    const activeManual = manualCases.filter(c => c.status === 'DONE').length;
    const activeCount = activeAuto + activeManual;
    const activeRate = total > 0 ? Math.round((activeCount / total) * 100) : 0;
    return { total, autoCount, manualCount, activeAuto, activeManual, activeCount, activeRate };
  }, [unifiedList, autoCases, manualCases]);

  const autoStatusData = useMemo(() => {
    return countByKey(autoCases, c => AUTO_STATUS_LABELS[c.status] || c.status);
  }, [autoCases]);

  const manualStatusData = useMemo(() => {
    const labels: Record<string, string> = {
      DRAFT: '草稿', PENDING_REVIEW: '待评审', IN_REVIEW: '评审中',
      REVISE: '修改中', DONE: '已完成', REJECTED: '已驳回',
    };
    return countByKey(manualCases, c => labels[c.status] || c.status);
  }, [manualCases]);

  const frameworkData = useMemo(() => {
    return countByKey(autoCases, c => c.framework || '其他');
  }, [autoCases]);

  const autoStatusColors = useMemo(() => {
    const map: Record<string, string> = {
      'Active': '#22c55e', 'Inactive': '#94a3b8', 'Draft': '#3b82f6', 'Deprecated': '#ef4444',
      'ACTIVE': '#22c55e', 'INACTIVE': '#94a3b8', 'DRAFT': '#3b82f6', 'DEPRECATED': '#ef4444',
    };
    return autoStatusData.map(d => map[d.name] || CHART_COLORS[autoStatusData.indexOf(d) % CHART_COLORS.length]);
  }, [autoStatusData]);

  const manualStatusColors = useMemo(() => {
    const map: Record<string, string> = {
      '已完成': '#22c55e', '待评审': '#3b82f6', '评审中': '#f59e0b',
      '修改中': '#ef4444', '已驳回': '#dc2626', '草稿': '#94a3b8',
    };
    return manualStatusData.map(d => map[d.name] || CHART_COLORS[manualStatusData.indexOf(d) % CHART_COLORS.length]);
  }, [manualStatusData]);

  if (loading && unifiedList.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-tertiary)' }}>
        加载中...
      </div>
    );
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      {/* ── Hero Banner ── */}
      <header style={S.hero}>
        <div style={S.heroGlow} />
        <div style={S.heroContent}>
          <div style={S.heroBadge}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20V10" /><path d="M18 20V4" /><path d="M6 20v-4" />
            </svg>
            <span>用例全景</span>
          </div>
          <h2 style={S.heroTitle}>测试用例看板</h2>
          <p style={S.heroDesc}>
            共 {stats.total} 个用例，自动化 {stats.autoCount} 个，手工 {stats.manualCount} 个，活跃率 {stats.activeRate}%
          </p>
          <div style={S.heroStats}>
            <div style={S.heroStatItem}>
              <span style={S.heroStatValue}>{stats.total}</span>
              <span style={S.heroStatLabel}>总用例</span>
            </div>
            <div style={S.heroStatDivider} />
            <div style={S.heroStatItem}>
              <span style={{ ...S.heroStatValue, color: '#06b6d4' }}>{stats.autoCount}</span>
              <span style={S.heroStatLabel}>自动化</span>
            </div>
            <div style={S.heroStatDivider} />
            <div style={S.heroStatItem}>
              <span style={{ ...S.heroStatValue, color: '#a855f7' }}>{stats.manualCount}</span>
              <span style={S.heroStatLabel}>手工</span>
            </div>
            <div style={S.heroStatDivider} />
            <div style={S.heroStatItem}>
              <span style={{ ...S.heroStatValue, color: '#22c55e' }}>{stats.activeRate}%</span>
              <span style={S.heroStatLabel}>活跃率</span>
            </div>
          </div>
        </div>
      </header>

      {/* ── KPI Cards ── */}
      <div className="dashboard-metric-grid">
        <div className="stat-card">
          <span className="stat-card__label">总用例</span>
          <span className="stat-card__value">{stats.total}</span>
          <span className="stat-card__delta" style={{ color: 'var(--text-tertiary)' }}>自动化 + 手工</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">自动化用例</span>
          <span className="stat-card__value" style={{ color: '#06b6d4' }}>{stats.autoCount}</span>
          <span className="stat-card__delta" style={{ color: '#22c55e' }}>{stats.activeAuto} 活跃</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">手工用例</span>
          <span className="stat-card__value" style={{ color: '#a855f7' }}>{stats.manualCount}</span>
          <span className="stat-card__delta" style={{ color: '#22c55e' }}>{stats.activeManual} 已完成</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">活跃总计</span>
          <span className="stat-card__value" style={{ color: '#22c55e' }}>{stats.activeCount}</span>
          <span className="stat-card__delta" style={{ color: 'var(--text-tertiary)' }}>占比 {stats.activeRate}%</span>
        </div>
      </div>

      {/* ── Charts ── */}
      <div className="dashboard-chart-grid">
        {/* Auto status pie */}
        <div className="chart-card">
          <h4 className="chart-card__title">自动化用例状态分布</h4>
          {autoStatusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={autoStatusData}
                  cx="50%" cy="50%"
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  labelLine={false}
                  label={renderPieLabel}
                >
                  {autoStatusData.map((_, i) => (
                    <Cell key={i} fill={autoStatusColors[i]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number, name: string) => [`${value} 个`, name]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 40, margin: 0 }}>暂无自动化用例</p>
          )}
        </div>

        {/* Manual status pie */}
        <div className="chart-card">
          <h4 className="chart-card__title">手工用例状态分布</h4>
          {manualStatusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={manualStatusData}
                  cx="50%" cy="50%"
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  labelLine={false}
                  label={renderPieLabel}
                >
                  {manualStatusData.map((_, i) => (
                    <Cell key={i} fill={manualStatusColors[i]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number, name: string) => [`${value} 个`, name]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 40, margin: 0 }}>暂无手工用例</p>
          )}
        </div>
      </div>

      {/* Framework bar chart */}
      {frameworkData.length > 0 && (
        <div className="chart-card" style={{ marginBottom: 0 }}>
          <h4 className="chart-card__title">自动化框架分布</h4>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={frameworkData} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value: number) => [`${value} 个`, '数量']} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {frameworkData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default TestCaseBoardStats;
