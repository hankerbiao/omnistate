import { useMemo, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, Line, Area, ComposedChart,
} from 'recharts'
import type { PieLabelRenderProps } from 'recharts'
import { WorkflowOverviewSection, type WorkflowNavigateTarget } from './workflow'
import { api } from '../services/api'
import type {
  AutomationTestCaseResponse,
  ExecutionAgent,
  ExecutionTask,
  RequirementResponse,
  TestCaseResponse,
} from '../types'
import { getStateLabel, getWorkflowStateStyle } from '../constants/workflowLabels'
import PageToolbar, { StatPill } from './ui/PageToolbar'
import {
  buildDemoDashboardData,
  DEMO_EXECUTIVE_METRICS,
  type DemoExecutiveMetrics,
} from '../mocks/dashboardDemoData'

type RangeKey = '7d' | '30d' | '90d' | 'all'

interface DashboardPageProps {
  onWorkflowNavigate?: (target: WorkflowNavigateTarget) => void;
}

interface DashboardData {
  requirements: RequirementResponse[];
  testCases: TestCaseResponse[];
  tasks: ExecutionTask[];
  agents: ExecutionAgent[];
  automationCases: AutomationTestCaseResponse[];
}

const RANGE_LABELS: Record<RangeKey, string> = { '7d': '近 7 天', '30d': '近 30 天', '90d': '近 90 天', all: '全部' }

const RANGE_DAYS: Record<RangeKey, number | null> = { '7d': 7, '30d': 30, '90d': 90, all: null }

const COLORS = {
  green: '#22c55e', red: '#ef4444', amber: '#f59e0b', purple: '#a855f7',
  cyan: '#06b6d4', blue: '#3b82f6', orange: '#f97316', pink: '#ec4899',
  slate: '#64748b',
}

const PRIORITY_COLORS: Record<string, string> = { P0: COLORS.red, P1: COLORS.amber, P2: COLORS.cyan, P3: COLORS.slate }
const CATEGORY_COLORS = [COLORS.blue, COLORS.green, COLORS.amber, COLORS.red, COLORS.purple]
const FRAMEWORK_COLORS = [COLORS.cyan, COLORS.amber, COLORS.blue, COLORS.slate]
const TYPE_COLORS = [COLORS.green, COLORS.blue, COLORS.amber, COLORS.purple]
const TASK_STATUS_COLORS: Record<string, string> = {
  PASSED: COLORS.green, SUCCESS: COLORS.green, COMPLETED: COLORS.green,
  FAILED: COLORS.red, DISPATCH_FAILED: COLORS.red,
  RUNNING: COLORS.amber, PENDING: COLORS.slate, QUEUED: COLORS.slate,
}

const RADIAN = Math.PI / 180

const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: PieLabelRenderProps) => {
  const radius = (innerRadius ?? 0) + ((outerRadius ?? 0) - (innerRadius ?? 0)) * 0.5
  const x = (cx ?? 0) + radius * Math.cos(-(midAngle ?? 0) * RADIAN)
  const y = (cy ?? 0) + radius * Math.sin(-(midAngle ?? 0) * RADIAN)
  return (percent ?? 0) > 0.05 ? (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {((percent ?? 0) * 100).toFixed(0)}%
    </text>
  ) : null
}

function countBy<T>(items: T[], keyFn: (item: T) => string): { name: string; value: number }[] {
  const map = items.reduce<Record<string, number>>((acc, item) => {
    const key = keyFn(item) || '未设置'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  return Object.entries(map)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}

function isTaskPassed(status: string) {
  return status === 'PASSED' || status === 'SUCCESS' || status === 'COMPLETED'
}

function isTaskFailed(status: string) {
  return status === 'FAILED' || status === 'DISPATCH_FAILED'
}

function isTaskRunning(status: string) {
  return status === 'RUNNING' || status === 'PENDING' || status === 'QUEUED'
}

function filterTasksByRange(tasks: ExecutionTask[], range: RangeKey): ExecutionTask[] {
  const days = RANGE_DAYS[range]
  if (days === null) return tasks
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
  return tasks.filter((t) => new Date(t.created_at).getTime() >= cutoff)
}

function buildDailyTrend(tasks: ExecutionTask[]) {
  const byDate = tasks.reduce<Record<string, { passed: number; failed: number; running: number }>>((acc, task) => {
    const d = new Date(task.created_at)
    const date = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    if (!acc[date]) acc[date] = { passed: 0, failed: 0, running: 0 }
    if (isTaskPassed(task.overall_status)) acc[date].passed += 1
    else if (isTaskFailed(task.overall_status)) acc[date].failed += 1
    else if (isTaskRunning(task.overall_status)) acc[date].running += 1
    return acc
  }, {})
  return Object.entries(byDate)
    .map(([date, stats]) => ({ date, ...stats }))
    .sort((a, b) => a.date.localeCompare(b.date))
}

interface TeamRow {
  user_id: string;
  owned_cases: number;
  owned_reqs: number;
  reviewed_cases: number;
}

function buildTeamRows(requirements: RequirementResponse[], testCases: TestCaseResponse[]): TeamRow[] {
  const map = new Map<string, TeamRow>()
  const ensure = (userId: string) => {
    if (!map.has(userId)) map.set(userId, { user_id: userId, owned_cases: 0, owned_reqs: 0, reviewed_cases: 0 })
    return map.get(userId)!
  }
  testCases.forEach((tc) => {
    if (tc.owner_id) ensure(tc.owner_id).owned_cases += 1
    if (tc.reviewer_id) ensure(tc.reviewer_id).reviewed_cases += 1
  })
  requirements.forEach((req) => {
    const owner = req.current_owner || req.tpm_owner_id
    if (owner) ensure(owner).owned_reqs += 1
  })
  return [...map.values()].sort((a, b) => b.owned_cases + b.owned_reqs - (a.owned_cases + a.owned_reqs))
}

export default function DashboardPage({ onWorkflowNavigate }: DashboardPageProps) {
  const [range, setRange] = useState<RangeKey>('30d')
  const [demoMode, setDemoMode] = useState(true)
  const demoData = useMemo(() => buildDemoDashboardData(), [])

  // 使用 React Query useQueries 批量加载 5 个数据集，利用全局 30s staleTime 去重
  const queries = useQueries({
    queries: [
      { queryKey: ['requirements'], queryFn: async () => (await api.listRequirements({ limit: 500 })).data || [], enabled: !demoMode },
      { queryKey: ['testCases'], queryFn: async () => (await api.listTestCases({ limit: 500 })).data || [], enabled: !demoMode },
      { queryKey: ['executionTasks'], queryFn: async () => (await api.listTasks({ limit: 500 })).data || [], enabled: !demoMode },
      { queryKey: ['executionAgents'], queryFn: async () => (await api.listAgents({})).data || [], enabled: !demoMode },
      { queryKey: ['automationTestCases'], queryFn: async () => (await api.listAutomationTestCases({ limit: 500 })).data || [], enabled: !demoMode },
    ],
  })

  const [reqQ, caseQ, taskQ, agentQ, autoQ] = queries
  const anyLoading = queries.some((q) => q.isLoading)
  const anyError = queries.find((q) => q.error)

  const data: DashboardData = {
    requirements: reqQ.data ?? [],
    testCases: caseQ.data ?? [],
    tasks: taskQ.data ?? [],
    agents: agentQ.data ?? [],
    automationCases: autoQ.data ?? [],
  }

  const activeData = demoMode ? demoData : data
  const executive = DEMO_EXECUTIVE_METRICS

  const filteredTasks = useMemo(
    () => filterTasksByRange(activeData.tasks, range),
    [activeData.tasks, range],
  )

  const taskSummary = useMemo(() => {
    let passed = 0
    let failed = 0
    let running = 0
    filteredTasks.forEach((t) => {
      if (isTaskPassed(t.overall_status)) passed += 1
      else if (isTaskFailed(t.overall_status)) failed += 1
      else if (isTaskRunning(t.overall_status)) running += 1
    })
    const total = filteredTasks.length
    const passRate = total > 0 ? Math.round((passed / total) * 1000) / 10 : 0
    return { total, passed, failed, running, passRate }
  }, [filteredTasks])

  const trends = useMemo(() => buildDailyTrend(filteredTasks), [filteredTasks])

  const statusItems = useMemo(
    () => countBy(activeData.testCases, (tc) => getStateLabel(tc.status, 'TEST_CASE')),
    [activeData.testCases],
  )

  const priorityItems = useMemo(
    () => countBy(activeData.testCases, (tc) => tc.priority || '未设置'),
    [activeData.testCases],
  )

  const categoryItems = useMemo(
    () => countBy(activeData.testCases, (tc) => tc.test_category || '未分类'),
    [activeData.testCases],
  )

  const reqCoverage = useMemo(() => {
    const casesByReq = activeData.testCases.reduce<Record<string, number>>((acc, tc) => {
      if (tc.ref_req_id) acc[tc.ref_req_id] = (acc[tc.ref_req_id] || 0) + 1
      return acc
    }, {})
    return activeData.requirements
      .map((req) => ({
        req_id: req.req_id,
        title: req.title,
        case_count: casesByReq[req.req_id] || 0,
        status: req.status,
        statusLabel: getStateLabel(req.status, 'REQUIREMENT'),
      }))
      .sort((a, b) => b.case_count - a.case_count)
  }, [activeData.requirements, activeData.testCases])

  const automatedCount = useMemo(
    () => activeData.testCases.filter((tc) => tc.is_automated || tc.is_need_auto).length,
    [activeData.testCases],
  )

  const automationRate = activeData.testCases.length > 0
    ? Math.round((automatedCount / activeData.testCases.length) * 1000) / 10
    : 0

  const frameworkDist = useMemo(
    () => countBy(activeData.automationCases, (ac) => ac.framework || '未设置'),
    [activeData.automationCases],
  )

  const typeDist = useMemo(
    () => countBy(activeData.automationCases, (ac) => ac.automation_type || '未设置'),
    [activeData.automationCases],
  )

  const teamRows = useMemo(
    () => buildTeamRows(activeData.requirements, activeData.testCases).slice(0, 10),
    [activeData.requirements, activeData.testCases],
  )

  const taskStatusItems = useMemo(
    () => countBy(filteredTasks, (t) => t.overall_status),
    [filteredTasks],
  )

  const onlineAgents = activeData.agents.filter((a) => a.is_online).length
  const activeCases = activeData.testCases.filter((tc) => tc.is_active).length
  const reqsWithCases = reqCoverage.filter((r) => r.case_count > 0).length

  const displayPassRate = demoMode ? 94.6 : taskSummary.passRate
  const displayTaskTotal = demoMode ? filteredTasks.length : taskSummary.total
  const displayPassed = demoMode
    ? Math.round(filteredTasks.length * 0.946)
    : taskSummary.passed
  const displayFailed = demoMode
    ? Math.round(filteredTasks.length * 0.038)
    : taskSummary.failed
  const displayRunning = demoMode
    ? filteredTasks.length - displayPassed - displayFailed
    : taskSummary.running

  const renderLabelList = (items: { name: string; value: number }[], colors: string[] | Record<string, string>) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', padding: '8px 0 0' }}>
      {items.map((d, i) => {
        const color = Array.isArray(colors) ? colors[i % colors.length] : (colors as Record<string, string>)[d.name] || COLORS.slate
        return (
          <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color, display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{d.value}</span>
          </div>
        )
      })}
    </div>
  )

  const taskPieData = [
    { name: '通过', value: displayPassed },
    { name: '失败', value: displayFailed },
    { name: '进行中', value: displayRunning },
  ].filter((d) => d.value > 0)

  const showContent = demoMode || !anyLoading

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="需求" value={activeData.requirements.length} />
            <StatPill label="用例" value={activeData.testCases.length} tone="info" />
            <StatPill label="任务" value={displayTaskTotal} tone="warning" />
            <StatPill label="Agent 在线" value={onlineAgents} tone="success" dot pulse={onlineAgents > 0} />
            {demoMode && <StatPill label="模式" value="演示" tone="info" />}
          </>
        )}
        actions={(
          <>
            <div className="segmented-control" role="group" aria-label="数据模式">
              <button
                type="button"
                className={`segmented-control__btn${demoMode ? ' segmented-control__btn--active' : ''}`}
                onClick={() => setDemoMode(true)}
              >
                汇报演示
              </button>
              <button
                type="button"
                className={`segmented-control__btn${!demoMode ? ' segmented-control__btn--active' : ''}`}
                onClick={() => setDemoMode(false)}
              >
                实时数据
              </button>
            </div>
            <div className="segmented-control" role="group" aria-label="时间范围">
              {(Object.entries(RANGE_LABELS) as [RangeKey, string][]).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={`segmented-control__btn${range === key ? ' segmented-control__btn--active' : ''}`}
                  onClick={() => setRange(key)}
                >
                  {label}
                </button>
              ))}
            </div>
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => queries.forEach(q => q.refetch?.())} disabled={demoMode}>
              刷新
            </button>
          </>
        )}
      />

      {demoMode && (
        <ExecutiveHero metrics={executive} />
      )}

      {anyError && !demoMode && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          {anyError.message || '加载统计数据失败'}
        </div>
      )}

      {!demoMode && <WorkflowOverviewSection onNavigate={onWorkflowNavigate} />}

      {!showContent ? (
        <div style={loadingBox}>
          <div className="loading-spinner" />
          <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>加载统计数据…</span>
        </div>
      ) : (
        <>
          {demoMode && (
            <div className="dashboard-kpi-grid">
              {executive.kpis.map((kpi) => (
                <KpiCard key={kpi.label} {...kpi} />
              ))}
            </div>
          )}

          <div className="stats-grid">
            <StatCard label="执行任务" value={displayTaskTotal.toLocaleString()} color={COLORS.purple} icon="▶" />
            <StatCard label="通过" value={displayPassed.toLocaleString()} color={COLORS.green} icon="✓" />
            <StatCard label="失败" value={displayFailed.toLocaleString()} color={COLORS.red} icon="✕" />
            <StatCard label="进行中" value={displayRunning.toLocaleString()} color={COLORS.amber} icon="◌" />
            <StatCard
              label="通过率"
              value={`${displayPassRate}%`}
              color={displayPassRate >= 80 ? COLORS.green : displayPassRate >= 60 ? COLORS.amber : COLORS.red}
              icon="%"
            />
            <StatCard label="测试用例" value={activeData.testCases.length.toLocaleString()} color={COLORS.blue} icon="◧" />
          </div>

          <div className="dashboard-metric-grid">
            <MetricBox label="测试用例编写需求" value={`${activeData.requirements.length}`} sub={`已关联用例: ${reqsWithCases}`} />
            <MetricBox label="激活用例" value={`${activeCases}`} sub={`总计: ${activeData.testCases.length}`} />
            <MetricBox
              label="自动化覆盖"
              value={demoMode ? `${executive.kpis[1].value}` : `${automationRate}%`}
              sub={`需/已自动化: ${automatedCount}`}
            />
            <MetricBox label="执行 Agent" value={`${activeData.agents.length}`} sub={`在线: ${onlineAgents}`} />
          </div>

          {demoMode && (
            <div className="dashboard-chart-grid">
              <div className="chart-card">
                <h3 className="chart-card__title">质量趋势 · 近 5 周</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={executive.weeklyQuality}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                    <XAxis dataKey="week" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="left" domain={[80, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="right" orientation="right" domain={[50, 80]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area yAxisId="left" type="monotone" dataKey="passRate" name="通过率 %" fill={`${COLORS.green}33`} stroke={COLORS.green} strokeWidth={2} />
                    <Line yAxisId="right" type="monotone" dataKey="coverage" name="自动化 %" stroke={COLORS.cyan} strokeWidth={2} dot={{ r: 4 }} />
                    <Bar yAxisId="right" dataKey="defects" name="缺陷数" fill={COLORS.red} opacity={0.7} barSize={16} radius={[3, 3, 0, 0]} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-card">
                <h3 className="chart-card__title">Lab 资产与通过率</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={executive.labCoverage} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} interval={0} angle={-12} textAnchor="end" height={56} />
                    <YAxis yAxisId="count" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="rate" orientation="right" domain={[85, 100]} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} unit="%" />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar yAxisId="count" dataKey="cases" name="用例数" fill={COLORS.blue} radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="count" dataKey="automated" name="已自动化" fill={COLORS.cyan} radius={[4, 4, 0, 0]} />
                    <Line yAxisId="rate" type="monotone" dataKey="passRate" name="通过率" stroke={COLORS.green} strokeWidth={2} dot={{ r: 4 }} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {demoMode && (
            <div className="chart-card" style={{ marginBottom: 16 }}>
              <h3 className="chart-card__title">里程碑进度</h3>
              <div style={milestoneGrid}>
                {executive.milestones.map((m) => (
                  <div key={m.name} style={milestoneCard}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 10 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{m.name}</span>
                      <MilestoneBadge status={m.status} />
                    </div>
                    <div style={milestoneBarTrack}>
                      <div
                        style={{
                          ...milestoneBarFill,
                          width: `${m.progress}%`,
                          backgroundColor: m.status === 'done' ? COLORS.green : m.status === 'at_risk' ? COLORS.amber : COLORS.blue,
                        }}
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                      <span>{m.progress}%</span>
                      <span>目标: {m.target}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="dashboard-chart-grid">
            <div className="chart-card">
              <h3 className="chart-card__title">每日执行趋势</h3>
              {trends.length === 0 ? (
                <EmptyHint text="所选时间范围内暂无执行任务" />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={trends} barGap={0} barCategoryGap="20%">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="passed" name="通过" stackId="a" fill={COLORS.green} radius={[2, 2, 0, 0]} />
                    <Bar dataKey="failed" name="失败" stackId="a" fill={COLORS.red} />
                    <Bar dataKey="running" name="进行中" stackId="a" fill={COLORS.amber} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="chart-card">
              <h3 className="chart-card__title">任务状态分布</h3>
              {taskPieData.length === 0 ? (
                <EmptyHint text="暂无执行任务数据" />
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 260 }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={taskPieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={renderCustomLabel} labelLine={false}>
                        {[COLORS.green, COLORS.red, COLORS.amber].map((c, i) => <Cell key={i} fill={c} />)}
                      </Pie>
                      <Legend wrapperStyle={{ fontSize: 11 }} formatter={(v) => <span style={{ color: 'var(--text-secondary)' }}>{v}</span>} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          <div className="dashboard-chart-grid">
            <div className="chart-card">
              <h3 className="chart-card__title">用例分布</h3>
              {activeData.testCases.length === 0 ? (
                <EmptyHint text="暂无测试用例" />
              ) : (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>工作流状态</div>
                      {statusItems.length > 0 && (
                        <>
                          <ResponsiveContainer width="100%" height={160}>
                            <PieChart>
                              <Pie data={statusItems} cx="50%" cy="50%" innerRadius={30} outerRadius={55} dataKey="value" label={renderCustomLabel} labelLine={false}>
                                {statusItems.map((e, i) => (
                                  <Cell key={e.name} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                                ))}
                              </Pie>
                            </PieChart>
                          </ResponsiveContainer>
                          {renderLabelList(statusItems, CATEGORY_COLORS)}
                        </>
                      )}
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>优先级</div>
                      {priorityItems.length > 0 && (
                        <>
                          <ResponsiveContainer width="100%" height={160}>
                            <PieChart>
                              <Pie data={priorityItems} cx="50%" cy="50%" innerRadius={30} outerRadius={55} dataKey="value" label={renderCustomLabel} labelLine={false}>
                                {priorityItems.map((e) => (
                                  <Cell key={e.name} fill={PRIORITY_COLORS[e.name] || COLORS.slate} />
                                ))}
                              </Pie>
                            </PieChart>
                          </ResponsiveContainer>
                          {renderLabelList(priorityItems, PRIORITY_COLORS)}
                        </>
                      )}
                    </div>
                  </div>
                  {categoryItems.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>测试类别</div>
                      <ResponsiveContainer width="100%" height={Math.max(120, categoryItems.length * 28)}>
                        <BarChart data={categoryItems} layout="vertical" barCategoryGap="20%">
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
                          <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                          <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={80} />
                          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)' }} />
                          <Bar dataKey="value" name="用例数" radius={[0, 4, 4, 0]}>
                            {categoryItems.map((_, i) => <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </>
              )}
            </div>
            <div className="chart-card">
              <h3 className="chart-card__title">需求用例关联</h3>
              {reqCoverage.length === 0 ? (
                <EmptyHint text="暂无测试用例编写需求" />
              ) : (
                <div style={tableWrap}>
                  <table style={table}>
                    <thead>
                      <tr>
                        <th style={{ ...th, width: 120 }}>需求 ID</th>
                        <th style={th}>需求名称</th>
                        <th style={{ ...th, textAlign: 'center', width: 70 }}>用例数</th>
                        <th style={{ ...th, width: 90 }}>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reqCoverage.slice(0, 12).map((req) => (
                        <tr key={req.req_id} style={tr}>
                          <td style={td}><span style={{ fontFamily: "'JetBrains Mono', monospace", color: COLORS.cyan, fontSize: 11 }}>{req.req_id}</span></td>
                          <td style={td}>{req.title}</td>
                          <td style={{ ...td, textAlign: 'center' }}>{req.case_count}</td>
                          <td style={td}>
                            <span className="status-badge" style={{ ...getWorkflowStateStyle(req.status), fontSize: 10, padding: '2px 6px' }}>
                              {req.statusLabel}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="dashboard-chart-grid">
            <div className="chart-card">
              <h3 className="chart-card__title">自动化用例</h3>
              {activeData.automationCases.length === 0 ? (
                <EmptyHint text="暂无自动化用例" />
              ) : (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>框架分布</div>
                      <ResponsiveContainer width="100%" height={160}>
                        <PieChart>
                          <Pie data={frameworkDist} cx="50%" cy="50%" innerRadius={35} outerRadius={60} dataKey="value" label={renderCustomLabel} labelLine={false}>
                            {frameworkDist.map((_, i) => <Cell key={i} fill={FRAMEWORK_COLORS[i % FRAMEWORK_COLORS.length]} />)}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      {renderLabelList(frameworkDist, FRAMEWORK_COLORS)}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, justifyContent: 'center' }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 32, fontWeight: 700, color: COLORS.cyan }}>{activeData.automationCases.length}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>自动化用例总数</div>
                      </div>
                      <div style={miniStatRow}>
                        <MiniStat label="手工用例自动化率" value={`${automationRate}%`} color={COLORS.blue} />
                      </div>
                    </div>
                  </div>
                  {typeDist.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>自动化类型</div>
                      <ResponsiveContainer width="100%" height={Math.max(80, typeDist.length * 28)}>
                        <BarChart data={typeDist} layout="vertical" barCategoryGap="20%">
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
                          <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                          <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={70} />
                          <Bar dataKey="value" name="数量" radius={[0, 4, 4, 0]}>
                            {typeDist.map((_, i) => <Cell key={i} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </>
              )}
            </div>
            <div className="chart-card">
              <h3 className="chart-card__title">任务原始状态</h3>
              {filteredTasks.length === 0 ? (
                <EmptyHint text="所选时间范围内暂无任务" />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={taskStatusItems} layout="vertical" barCategoryGap="20%">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={100} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)' }} />
                    <Bar dataKey="value" name="任务数" radius={[0, 4, 4, 0]}>
                      {taskStatusItems.map((item, i) => (
                        <Cell key={item.name} fill={TASK_STATUS_COLORS[item.name] || CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="chart-card" style={{ marginBottom: 16 }}>
            <h3 className="chart-card__title">{demoMode ? '团队效能排行' : '负责人负载（来自用例/需求 owner）'}</h3>
            {demoMode ? (
              executive.teamPerformance.length === 0 ? (
                <EmptyHint text="暂无团队数据" />
              ) : (
                <div style={tableWrap}>
                  <table style={table}>
                    <thead>
                      <tr>
                        <th style={th}>成员</th>
                        <th style={th}>部门</th>
                        <th style={{ ...th, textAlign: 'center' }}>负责用例</th>
                        <th style={{ ...th, textAlign: 'center' }}>负责需求</th>
                        <th style={{ ...th, textAlign: 'center' }}>审核</th>
                        <th style={{ ...th, textAlign: 'center', width: 90 }}>完成率</th>
                        <th style={{ ...th, width: 140 }}>负载</th>
                      </tr>
                    </thead>
                    <tbody>
                      {executive.teamPerformance.map((u, i) => {
                        const load = u.owned_cases + u.owned_reqs
                        const maxLoad = Math.max(...executive.teamPerformance.map((x) => x.owned_cases + x.owned_reqs), 1)
                        const loadPct = (load / maxLoad) * 100
                        return (
                          <tr key={u.name} style={{ ...tr, ...(i % 2 === 1 ? { backgroundColor: 'rgba(0,0,0,0.02)' } : {}) }}>
                            <td style={td}>
                              <div style={{ fontWeight: 600 }}>{u.name}</div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.role}</div>
                            </td>
                            <td style={{ ...td, fontSize: 12, color: 'var(--text-secondary)' }}>{u.dept}</td>
                            <td style={{ ...td, textAlign: 'center' }}>{u.owned_cases}</td>
                            <td style={{ ...td, textAlign: 'center' }}>{u.owned_reqs}</td>
                            <td style={{ ...td, textAlign: 'center' }}>{u.reviewed_cases}</td>
                            <td style={{ ...td, textAlign: 'center' }}>
                              <span style={{ color: u.completionRate >= 90 ? COLORS.green : COLORS.amber, fontWeight: 600 }}>
                                {u.completionRate}%
                              </span>
                            </td>
                            <td style={td}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ flex: 1, height: 8, backgroundColor: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden' }}>
                                  <div style={{ height: '100%', width: `${loadPct}%`, backgroundColor: COLORS.cyan, borderRadius: 4 }} />
                                </div>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )
            ) : teamRows.length === 0 ? (
              <EmptyHint text="暂无负责人数据" />
            ) : (
              <div style={tableWrap}>
                <table style={table}>
                  <thead>
                    <tr>
                      <th style={{ ...th, width: 120 }}>用户 ID</th>
                      <th style={{ ...th, textAlign: 'center' }}>负责用例</th>
                      <th style={{ ...th, textAlign: 'center' }}>负责需求</th>
                      <th style={{ ...th, textAlign: 'center' }}>审核用例</th>
                      <th style={{ ...th, width: 140 }}>负载条</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teamRows.map((u, i) => {
                      const load = u.owned_cases + u.owned_reqs
                      const maxLoad = Math.max(...teamRows.map((x) => x.owned_cases + x.owned_reqs), 1)
                      const loadPct = (load / maxLoad) * 100
                      return (
                        <tr key={u.user_id} style={{ ...tr, ...(i % 2 === 1 ? { backgroundColor: 'rgba(0,0,0,0.02)' } : {}) }}>
                          <td style={td}><span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: COLORS.purple }}>{u.user_id}</span></td>
                          <td style={{ ...td, textAlign: 'center' }}>{u.owned_cases}</td>
                          <td style={{ ...td, textAlign: 'center' }}>{u.owned_reqs}</td>
                          <td style={{ ...td, textAlign: 'center' }}>{u.reviewed_cases}</td>
                          <td style={td}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <div style={{ flex: 1, height: 8, backgroundColor: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${loadPct}%`, backgroundColor: COLORS.cyan, borderRadius: 4 }} />
                              </div>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{load}</span>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="chart-card">
            <h3 className="chart-card__title">数据摘要</h3>
            <div style={summaryGrid}>
              <SummaryBox label="测试用例编写需求" value={`${activeData.requirements.length}`} />
              <SummaryBox label="测试用例" value={`${activeData.testCases.length}`} />
              <SummaryBox label="自动化用例" value={`${activeData.automationCases.length}`} />
              <SummaryBox label="执行任务" value={`${activeData.tasks.length}`} />
              <SummaryBox label="执行 Agent" value={`${activeData.agents.length}`} />
              <SummaryBox label="在线 Agent" value={`${onlineAgents}`} />
              <SummaryBox label="自动化率" value={demoMode ? executive.kpis[1].value : `${automationRate}%`} />
              <SummaryBox label="数据刷新" value={new Date().toLocaleTimeString('zh-CN')} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function ExecutiveHero({ metrics }: { metrics: DemoExecutiveMetrics }) {
  const scoreColor = metrics.healthScore >= 90 ? COLORS.green : metrics.healthScore >= 75 ? COLORS.amber : COLORS.red
  return (
    <div style={heroWrap}>
      <div style={heroMain}>
        <div style={heroBadge}>质量周报 · {metrics.periodLabel}</div>
        <h2 style={heroTitle}>服务器测试质量驾驶舱</h2>
        <p style={heroSummary}>{metrics.healthSummary}</p>
        <div style={heroHighlights}>
          {metrics.highlights.map((h) => (
            <div key={h.title} style={{ ...heroHighlight, borderLeft: `3px solid ${h.type === 'success' ? COLORS.green : h.type === 'warning' ? COLORS.amber : COLORS.blue}` }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>{h.title}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{h.detail}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={heroScore}>
        <div style={{ ...scoreRing, border: `4px solid ${scoreColor}`, color: scoreColor }}>
          <span style={{ fontSize: 36, fontWeight: 800, lineHeight: 1 }}>{metrics.healthScore}</span>
          <span style={{ fontSize: 11, opacity: 0.85 }}>健康分</span>
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, color: scoreColor, marginTop: 10 }}>{metrics.healthGrade}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{metrics.reportDate}</div>
      </div>
    </div>
  )
}

function KpiCard({ label, value, delta, deltaUp, sub, color }: DemoExecutiveMetrics['kpis'][0]) {
  return (
    <div style={kpiCard}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontSize: 24, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: deltaUp ? COLORS.green : COLORS.red }}>
          {deltaUp ? '↑' : '↓'} {delta}
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>{sub}</div>
    </div>
  )
}

function MilestoneBadge({ status }: { status: 'on_track' | 'at_risk' | 'done' }) {
  const map = {
    on_track: { label: '正常', bg: `${COLORS.blue}22`, color: COLORS.blue },
    at_risk: { label: '需关注', bg: `${COLORS.amber}22`, color: COLORS.amber },
    done: { label: '已完成', bg: `${COLORS.green}22`, color: COLORS.green },
  }
  const s = map[status]
  return (
    <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, backgroundColor: s.bg, color: s.color, whiteSpace: 'nowrap' }}>
      {s.label}
    </span>
  )
}

function StatCard({ label, value, color, icon }: { label: string; value: string; color: string; icon: string }) {
  return (
    <div className="stat-card" style={statCard}>
      <div style={{ ...statIcon, backgroundColor: `${color}18`, color }}>{icon}</div>
      <div>
        <div className="stat-card__label">{label}</div>
        <div className="stat-card__value" style={{ color }}>{value}</div>
      </div>
    </div>
  )
}

function MetricBox({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="stat-card" style={metricBox}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</div>
    </div>
  )
}

function SummaryBox({ label, value }: { label: string; value: string }) {
  return (
    <div style={sbox}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
    </div>
  )
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
      {text}
    </div>
  )
}

const loadingBox: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: 48,
}

const statCard: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 14,
  padding: '18px 20px', backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-default)',
}
const statIcon: React.CSSProperties = {
  width: 42, height: 42, display: 'flex', alignItems: 'center', justifyContent: 'center',
  borderRadius: 12, fontSize: 18, fontWeight: 700, flexShrink: 0,
}
const metricBox: React.CSSProperties = {
  padding: '16px 20px', backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-default)',
}

const tableWrap: React.CSSProperties = { overflowX: 'auto' }
const table: React.CSSProperties = { width: '100%', borderCollapse: 'collapse' }
const th: React.CSSProperties = {
  padding: '10px 10px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)',
  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.3px',
  borderBottom: '1px solid var(--border-muted)', whiteSpace: 'nowrap',
}
const tr: React.CSSProperties = { borderBottom: '1px solid var(--border-muted)' }
const td: React.CSSProperties = { padding: '10px 10px', fontSize: 13, color: 'var(--text-primary)' }

const miniStatRow: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-around',
}

const summaryGrid: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 10,
}
const sbox: React.CSSProperties = {
  padding: 12, backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)',
}

const heroWrap: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'stretch',
  gap: 24,
  marginBottom: 20,
  padding: '24px 28px',
  borderRadius: 'var(--radius-xl)',
  border: '1px solid var(--border-subtle)',
  background: 'linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(6,182,212,0.06) 50%, rgba(34,197,94,0.05) 100%)',
  flexWrap: 'wrap',
}

const heroMain: React.CSSProperties = { flex: 1, minWidth: 280 }

const heroBadge: React.CSSProperties = {
  display: 'inline-block',
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--accent-primary)',
  backgroundColor: 'rgba(59,130,246,0.12)',
  padding: '4px 10px',
  borderRadius: 999,
  marginBottom: 10,
}

const heroTitle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: 22,
  fontWeight: 700,
  color: 'var(--text-primary)',
}

const heroSummary: React.CSSProperties = {
  margin: '0 0 16px',
  fontSize: 13,
  color: 'var(--text-secondary)',
  lineHeight: 1.6,
  maxWidth: 640,
}

const heroHighlights: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 10,
}

const heroHighlight: React.CSSProperties = {
  padding: '10px 12px',
  backgroundColor: 'var(--surface-primary)',
  borderRadius: 'var(--radius-md)',
  borderLeft: '3px solid',
}

const heroScore: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: 120,
}

const scoreRing: React.CSSProperties = {
  width: 96,
  height: 96,
  borderRadius: '50%',
  border: '4px solid',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: 'var(--surface-primary)',
}

const kpiCard: React.CSSProperties = {
  padding: '16px 18px',
  backgroundColor: 'var(--surface-primary)',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-subtle)',
  boxShadow: 'var(--shadow-sm)',
}

const milestoneGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 14,
}

const milestoneCard: React.CSSProperties = {
  padding: 14,
  backgroundColor: 'var(--bg-tertiary)',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-muted)',
}

const milestoneBarTrack: React.CSSProperties = {
  height: 8,
  backgroundColor: 'var(--surface-primary)',
  borderRadius: 4,
  overflow: 'hidden',
}

const milestoneBarFill: React.CSSProperties = {
  height: '100%',
  borderRadius: 4,
  transition: 'width 0.4s ease',
}
