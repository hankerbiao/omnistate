import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

type RangeKey = '7d' | '30d' | '90d' | 'all'

// ─── Mock Data ─────────────────────────────────────────────

const DAILY_TRENDS: Record<RangeKey, { date: string; passed: number; failed: number; running: number }[]> = {
  '7d': [
    { date: '05-14', passed: 22, failed: 5, running: 3 },
    { date: '05-15', passed: 35, failed: 2, running: 1 },
    { date: '05-16', passed: 18, failed: 7, running: 2 },
    { date: '05-17', passed: 30, failed: 4, running: 4 },
    { date: '05-18', passed: 25, failed: 6, running: 2 },
    { date: '05-19', passed: 20, failed: 8, running: 1 },
    { date: '05-20', passed: 27, failed: 3, running: 3 },
  ],
  '30d': [
    { date: '04-21', passed: 28, failed: 3, running: 2 },
    { date: '04-22', passed: 19, failed: 6, running: 1 },
    { date: '04-23', passed: 31, failed: 4, running: 3 },
    { date: '04-24', passed: 24, failed: 2, running: 2 },
    { date: '04-25', passed: 15, failed: 8, running: 1 },
    { date: '04-26', passed: 33, failed: 5, running: 4 },
    { date: '04-27', passed: 27, failed: 3, running: 2 },
    { date: '04-28', passed: 21, failed: 7, running: 3 },
    { date: '04-29', passed: 36, failed: 1, running: 2 },
    { date: '04-30', passed: 29, failed: 5, running: 1 },
    { date: '05-01', passed: 17, failed: 9, running: 3 },
    { date: '05-02', passed: 26, failed: 4, running: 2 },
    { date: '05-03', passed: 32, failed: 2, running: 1 },
    { date: '05-04', passed: 23, failed: 6, running: 4 },
    { date: '05-05', passed: 30, failed: 3, running: 2 },
    { date: '05-06', passed: 20, failed: 7, running: 1 },
    { date: '05-07', passed: 34, failed: 2, running: 3 },
    { date: '05-08', passed: 28, failed: 5, running: 2 },
    { date: '05-09', passed: 16, failed: 8, running: 1 },
    { date: '05-10', passed: 22, failed: 4, running: 2 },
    { date: '05-11', passed: 37, failed: 1, running: 3 },
    { date: '05-12', passed: 25, failed: 6, running: 2 },
    { date: '05-13', passed: 31, failed: 3, running: 1 },
    { date: '05-14', passed: 22, failed: 5, running: 3 },
    { date: '05-15', passed: 35, failed: 2, running: 1 },
    { date: '05-16', passed: 18, failed: 7, running: 2 },
    { date: '05-17', passed: 30, failed: 4, running: 4 },
    { date: '05-18', passed: 25, failed: 6, running: 2 },
    { date: '05-19', passed: 20, failed: 8, running: 1 },
    { date: '05-20', passed: 27, failed: 3, running: 3 },
  ],
  '90d': [],
  'all': [],
}

// Fill 90d and all with extended data
for (let i = 0; i < 60; i++) {
  const d = new Date(2026, 2, 22 + i)
  const dateStr = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  DAILY_TRENDS['90d'].push({
    date: dateStr,
    passed: 18 + Math.floor(Math.random() * 20),
    failed: 1 + Math.floor(Math.random() * 8),
    running: Math.floor(Math.random() * 4),
  })
}
DAILY_TRENDS['all'] = [...DAILY_TRENDS['90d']]

const TOP_FREQUENT = [
  { case_id: 'TC-MEM-001', title: 'DDR5 内存带宽测试', execution_count: 15, pass_count: 12, fail_count: 3, pass_rate: 80 },
  { case_id: 'TC-MEM-005', title: '内存压力测试 72H', execution_count: 12, pass_count: 9, fail_count: 3, pass_rate: 75 },
  { case_id: 'TC-CPU-002', title: 'CPU 全核负载测试', execution_count: 11, pass_count: 10, fail_count: 1, pass_rate: 90.9 },
  { case_id: 'TC-MEM-003', title: '内存读写延迟测试', execution_count: 10, pass_count: 6, fail_count: 4, pass_rate: 60 },
  { case_id: 'TC-DISK-001', title: 'NVMe 顺序读写测试', execution_count: 9, pass_count: 8, fail_count: 1, pass_rate: 88.9 },
  { case_id: 'TC-NET-002', title: 'RDMA 网络延迟测试', execution_count: 8, pass_count: 7, fail_count: 1, pass_rate: 87.5 },
  { case_id: 'TC-PCIE-001', title: 'PCIe Gen5 带宽测试', execution_count: 7, pass_count: 6, fail_count: 1, pass_rate: 85.7 },
  { case_id: 'TC-MEM-007', title: '内存混插兼容性测试', execution_count: 7, pass_count: 4, fail_count: 3, pass_rate: 57.1 },
  { case_id: 'TC-CPU-005', title: 'CPU AVX-512 指令集测试', execution_count: 6, pass_count: 6, fail_count: 0, pass_rate: 100 },
  { case_id: 'TC-NET-001', title: '万兆网卡吞吐量测试', execution_count: 6, pass_count: 5, fail_count: 1, pass_rate: 83.3 },
]

const FLAKY_CASES = [
  { case_id: 'TC-MEM-003', title: '内存读写延迟测试', execution_count: 10, pass_count: 6, fail_count: 4, pass_rate: 60 },
  { case_id: 'TC-MEM-007', title: '内存混插兼容性测试', execution_count: 7, pass_count: 4, fail_count: 3, pass_rate: 57.1 },
  { case_id: 'TC-MEM-001', title: 'DDR5 内存带宽测试', execution_count: 15, pass_count: 12, fail_count: 3, pass_rate: 80 },
  { case_id: 'TC-MEM-005', title: '内存压力测试 72H', execution_count: 12, pass_count: 9, fail_count: 3, pass_rate: 75 },
  { case_id: 'TC-DISK-003', title: '磁盘 IOPS 混合读写测试', execution_count: 5, pass_count: 3, fail_count: 2, pass_rate: 60 },
  { case_id: 'TC-PCIE-002', title: 'PCIe 链路稳定性测试', execution_count: 4, pass_count: 2, fail_count: 2, pass_rate: 50 },
  { case_id: 'TC-NET-003', title: 'TCP 吞吐量压力测试', execution_count: 5, pass_count: 3, fail_count: 2, pass_rate: 60 },
  { case_id: 'TC-CPU-003', title: 'CPU 虚拟化支持测试', execution_count: 3, pass_count: 2, fail_count: 1, pass_rate: 66.7 },
  { case_id: 'TC-SEC-001', title: 'TPM 安全启动测试', execution_count: 3, pass_count: 2, fail_count: 1, pass_rate: 66.7 },
  { case_id: 'TC-MEM-002', title: '内存 ECC 纠错测试', execution_count: 4, pass_count: 3, fail_count: 1, pass_rate: 75 },
]

const REQ_COVERAGE = [
  { req_id: 'REQ-MEM-001', title: 'DDR5 内存子系统验证', case_count: 8, executed_count: 7, passed_count: 5, pass_rate: 71.4 },
  { req_id: 'REQ-CPU-001', title: 'CPU 功能与性能验证', case_count: 6, executed_count: 6, passed_count: 6, pass_rate: 100 },
  { req_id: 'REQ-DISK-001', title: 'NVMe 存储验证', case_count: 5, executed_count: 4, passed_count: 4, pass_rate: 100 },
  { req_id: 'REQ-NET-001', title: '高速网络验证', case_count: 7, executed_count: 5, passed_count: 4, pass_rate: 80 },
  { req_id: 'REQ-PCIE-001', title: 'PCIe Gen5 总线验证', case_count: 4, executed_count: 4, passed_count: 3, pass_rate: 75 },
  { req_id: 'REQ-SEC-001', title: '安全特性验证', case_count: 3, executed_count: 2, passed_count: 2, pass_rate: 100 },
  { req_id: 'REQ-COMPAT-001', title: '兼容性验证', case_count: 5, executed_count: 3, passed_count: 2, pass_rate: 66.7 },
  { req_id: 'REQ-STRESS-001', title: '压力与稳定性验证', case_count: 6, executed_count: 5, passed_count: 4, pass_rate: 80 },
  { req_id: 'REQ-POWER-001', title: '功耗与散热验证', case_count: 4, executed_count: 2, passed_count: 1, pass_rate: 50 },
]

const TEAM_PERFORMANCE = [
  { user_id: 'zhangsan', username: '张三', owned_cases: 15, owned_reqs: 3, created_tasks: 28, reviewed_cases: 4 },
  { user_id: 'lisi', username: '李四', owned_cases: 12, owned_reqs: 2, created_tasks: 35, reviewed_cases: 6 },
  { user_id: 'wangwu', username: '王五', owned_cases: 8, owned_reqs: 4, created_tasks: 15, reviewed_cases: 2 },
  { user_id: 'zhaoliu', username: '赵六', owned_cases: 6, owned_reqs: 1, created_tasks: 42, reviewed_cases: 3 },
  { user_id: 'sunqi', username: '孙七', owned_cases: 10, owned_reqs: 2, created_tasks: 20, reviewed_cases: 5 },
  { user_id: 'zhouba', username: '周八', owned_cases: 4, owned_reqs: 3, created_tasks: 8, reviewed_cases: 1 },
]

const RANGE_LABELS: Record<RangeKey, string> = { '7d': '近 7 天', '30d': '近 30 天', '90d': '近 90 天', all: '全部' }

const SUMMARY_STATS: Record<RangeKey, {
  total_tasks: number; passed: number; failed: number; running: number; queued: number; pass_rate: number
}> = {
  '7d': { total_tasks: 248, passed: 195, failed: 38, running: 15, queued: 0, pass_rate: 83.7 },
  '30d': { total_tasks: 1056, passed: 862, failed: 146, running: 48, queued: 0, pass_rate: 85.5 },
  '90d': { total_tasks: 3218, passed: 2680, failed: 402, running: 136, queued: 0, pass_rate: 87 },
  all: { total_tasks: 8542, passed: 7210, failed: 958, running: 374, queued: 0, pass_rate: 88.3 },
}

const STATUS_DIST = { DRAFT: 23, APPROVED: 45, ACTIVE: 68, DEPRECATED: 15, REJECTED: 5 }
const PRIORITY_DIST = { P0: 12, P1: 38, P2: 64, P3: 42 }
const CATEGORY_DIST = { '功能测试': 78, '性能测试': 35, '兼容性测试': 22, '安全测试': 15, '稳定性测试': 6 }
const STATUS_ITEMS = Object.entries(STATUS_DIST).map(([k, v]) => ({ name: k, value: v }))
const PRIORITY_ITEMS = Object.entries(PRIORITY_DIST).map(([k, v]) => ({ name: k, value: v }))
const CATEGORY_ITEMS = Object.entries(CATEGORY_DIST).map(([k, v]) => ({ name: k, value: v }))
const totalCases = Object.values(STATUS_DIST).reduce((a, b) => a + b, 0)

const AUTOMATION_DATA = {
  total_auto: 86, active: 72, deprecated: 14,
  automation_rate: 68.5,
  framework_dist: { pytest: 45, robotframework: 22, junit: 12, other: 7 },
  type_dist: { 接口测试: 38, UI测试: 25, 单元测试: 15, 性能测试: 8 },
}

const WORKFLOW_DATA = [
  { type: 'REQUIREMENT', state: 'DRAFT', count: 8, avg_hours: 24 },
  { type: 'REQUIREMENT', state: 'PENDING_REVIEW', count: 12, avg_hours: 48 },
  { type: 'REQUIREMENT', state: 'DEVELOPING', count: 18, avg_hours: 72 },
  { type: 'REQUIREMENT', state: 'PENDING_TEST', count: 7, avg_hours: 36 },
  { type: 'REQUIREMENT', state: 'RELEASED', count: 45, avg_hours: 16 },
  { type: 'TEST_CASE', state: 'DRAFT', count: 23, avg_hours: 12 },
  { type: 'TEST_CASE', state: 'PENDING_REVIEW', count: 30, avg_hours: 36 },
  { type: 'TEST_CASE', state: 'APPROVED', count: 45, avg_hours: 18 },
  { type: 'TEST_CASE', state: 'ACTIVE', count: 68, avg_hours: 8 },
  { type: 'TEST_CASE', state: 'DEPRECATED', count: 15, avg_hours: 4 },
]

const COLORS = {
  green: '#22c55e', red: '#ef4444', amber: '#f59e0b', purple: '#a855f7',
  cyan: '#06b6d4', blue: '#3b82f6', orange: '#f97316', pink: '#ec4899',
  slate: '#64748b',
}

const STATUS_COLORS: Record<string, string> = {
  DRAFT: COLORS.slate, APPROVED: COLORS.green, ACTIVE: COLORS.cyan,
  DEPRECATED: COLORS.purple, REJECTED: COLORS.red,
}
const PRIORITY_COLORS: Record<string, string> = { P0: COLORS.red, P1: COLORS.amber, P2: COLORS.cyan, P3: COLORS.slate }
const CATEGORY_COLORS = [COLORS.blue, COLORS.green, COLORS.amber, COLORS.red, COLORS.purple]
const FRAMEWORK_COLORS = [COLORS.cyan, COLORS.amber, COLORS.blue, COLORS.slate]
const TYPE_COLORS = [COLORS.green, COLORS.blue, COLORS.amber, COLORS.purple]
const WF_COLORS = [COLORS.slate, COLORS.amber, COLORS.blue, COLORS.green, COLORS.purple, COLORS.cyan, COLORS.orange, COLORS.pink, COLORS.red, COLORS.slate.slice(0, -1) + '0']

const PASS_RATE_COLOR = (r: number) => r >= 80 ? COLORS.green : r >= 60 ? COLORS.amber : COLORS.red

const RADIAN = Math.PI / 180
import type { PieLabelRenderProps } from 'recharts'

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

// ─── Component ─────────────────────────────────────────────

export default function DashboardPage() {
  const [range, setRange] = useState<RangeKey>('7d')
  const [topTab, setTopTab] = useState<'frequent' | 'flaky'>('frequent')

  const summary = SUMMARY_STATS[range]
  const trends = useMemo(() => DAILY_TRENDS[range] || DAILY_TRENDS['7d'], [range])
  const topItems = useMemo(() => topTab === 'frequent' ? TOP_FREQUENT.slice(0, 6) : FLAKY_CASES.slice(0, 6), [topTab])
  const avgDuration = useMemo(() => {
    return range === '7d' ? '12m 34s' : range === '30d' ? '15m 21s' : range === '90d' ? '14m 08s' : '13m 45s'
  }, [range])

  const renderLabelList = (data: { name: string; value: number }[], colors: (string | Record<string, string>)[] | Record<string, string>) => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', padding: '8px 0 0' }}>
      {data.map((d, i) => {
        const color = Array.isArray(colors) ? colors[i % colors.length] : (colors as Record<string, string>)[d.name] || COLORS.slate
        return (
          <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color as string, display: 'inline-block' }} />
            <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{d.value}</span>
          </div>
        )
      })}
    </div>
  )

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>数据统计看板</h1>
          <p style={subtitleStyle}>全方位掌握测试任务、用例、需求与团队状态</p>
        </div>
        <div style={rangeGroupStyle}>
          {(Object.entries(RANGE_LABELS) as [RangeKey, string][]).map(([key, label]) => (
            <button key={key} onClick={() => setRange(key)}
              style={{ ...rangeBtn, ...(range === key ? rangeBtnActive : {}) }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Row 1: Execution Summary Cards */}
      <div style={cardsGrid}>
        <StatCard label="总执行次数" value={summary.total_tasks.toLocaleString()} color={COLORS.purple} icon="▶" />
        <StatCard label="通过" value={summary.passed.toLocaleString()} color={COLORS.green} icon="✓" />
        <StatCard label="失败" value={summary.failed.toLocaleString()} color={COLORS.red} icon="✕" />
        <StatCard label="执行中" value={summary.running.toLocaleString()} color={COLORS.amber} icon="◌" />
        <StatCard label="通过率" value={`${summary.pass_rate}%`} color={COLORS.cyan} icon="%" />
        <StatCard label="平均耗时" value={avgDuration} color={COLORS.blue} icon="⏱" />
      </div>

      {/* Row 2: Overview Metrics */}
      <div style={metricsRow}>
        <MetricBox label="总用例数" value={`${totalCases}`} sub="激活中: 68" />
        <MetricBox label="自动化覆盖率" value="68.5%" sub="已关联: 86 项" />
        <MetricBox label="总需求数" value="9" sub="已覆盖: 7" />
        <MetricBox label="执行 Agent" value="6" sub="在线: 4" />
      </div>

      {/* Row 3: Daily Trend + Task Status */}
      <div style={twoCol}>
        <div style={cardSection}>
          <h3 style={cardSectionTitle}>每日执行趋势</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trends} barGap={0} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: 'var(--text-primary)', fontWeight: 600 }}
              />
              <Bar dataKey="passed" name="通过" stackId="a" fill={COLORS.green} radius={[2, 2, 0, 0]} />
              <Bar dataKey="failed" name="失败" stackId="a" fill={COLORS.red} radius={[2, 2, 0, 0]} />
              <Bar dataKey="running" name="执行中" stackId="a" fill={COLORS.amber} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div style={cardSection}>
          <h3 style={cardSectionTitle}>任务状态分布</h3>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 260 }}>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={[
                  { name: '通过', value: summary.passed },
                  { name: '失败', value: summary.failed },
                  { name: '执行中', value: summary.running },
                  { name: '排队', value: summary.queued || 0 },
                ].filter(d => d.value > 0)} cx="50%" cy="50%" outerRadius={80}
                  dataKey="value" label={renderCustomLabel} labelLine={false}>
                  {[COLORS.green, COLORS.red, COLORS.amber, COLORS.slate].map((c, i) => (
                    <Cell key={i} fill={c} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 11 }}
                  formatter={(value: string) => <span style={{ color: 'var(--text-secondary)' }}>{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 4: Distributions + Top-N */}
      <div style={twoCol}>
        <div style={cardSection}>
          <h3 style={cardSectionTitle}>用例分布</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>工作流状态</div>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={STATUS_ITEMS} cx="50%" cy="50%" innerRadius={30} outerRadius={55}
                    dataKey="value" label={renderCustomLabel} labelLine={false}>
                    {STATUS_ITEMS.map(e => <Cell key={e.name} fill={STATUS_COLORS[e.name] || COLORS.slate} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              {renderLabelList(STATUS_ITEMS, STATUS_COLORS)}
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>优先级</div>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={PRIORITY_ITEMS} cx="50%" cy="50%" innerRadius={30} outerRadius={55}
                    dataKey="value" label={renderCustomLabel} labelLine={false}>
                    {PRIORITY_ITEMS.map(e => <Cell key={e.name} fill={PRIORITY_COLORS[e.name] || COLORS.slate} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              {renderLabelList(PRIORITY_ITEMS, PRIORITY_COLORS)}
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>测试类别分布</div>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={CATEGORY_ITEMS} layout="vertical" barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={70} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)' }} />
                <Bar dataKey="value" name="用例数" radius={[0, 4, 4, 0]}>
                  {CATEGORY_ITEMS.map((_, i) => <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div style={cardSection}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ ...cardSectionTitle, margin: 0 }}>Top-N 排行</h3>
            <div style={tabGroup}>
              <button onClick={() => setTopTab('frequent')} style={{ ...tabBtn, ...(topTab === 'frequent' ? tabBtnActive : {}) }}>最频繁</button>
              <button onClick={() => setTopTab('flaky')} style={{ ...tabBtn, ...(topTab === 'flaky' ? tabBtnActive : {}) }}>高失败率</button>
            </div>
          </div>
          <div style={tableWrap}>
            <table style={table}>
              <thead>
                <tr>
                  <th style={{ ...th, width: 105 }}>用例 ID</th>
                  <th style={th}>名称</th>
                  <th style={{ ...th, textAlign: 'center', width: 44 }}>总</th>
                  <th style={{ ...th, textAlign: 'center', width: 44 }}>通过</th>
                  <th style={{ ...th, textAlign: 'center', width: 44 }}>失败</th>
                  <th style={{ ...th, textAlign: 'center', width: 56 }}>通过率</th>
                </tr>
              </thead>
              <tbody>
                {topItems.map((item, i) => (
                  <tr key={item.case_id} style={{ ...tr, ...(i % 2 === 1 ? { backgroundColor: 'rgba(0,0,0,0.02)' } : {}) }}>
                    <td style={td}><span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: COLORS.purple }}>{item.case_id}</span></td>
                    <td style={td}>{item.title}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{item.execution_count}</td>
                    <td style={{ ...td, textAlign: 'center', color: COLORS.green }}>{item.pass_count}</td>
                    <td style={{ ...td, textAlign: 'center', color: item.fail_count > 0 ? COLORS.red : 'inherit' }}>{item.fail_count}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span style={{ fontWeight: 600, color: PASS_RATE_COLOR(item.pass_rate) }}>{item.pass_rate}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Row 5: Requirement Coverage */}
      <div style={cardSection}>
        <h3 style={cardSectionTitle}>需求覆盖率</h3>
        <div style={tableWrap}>
          <table style={table}>
            <thead>
              <tr>
                <th style={{ ...th, width: 120 }}>需求 ID</th>
                <th style={th}>需求名称</th>
                <th style={{ ...th, textAlign: 'center', width: 50 }}>用例数</th>
                <th style={{ ...th, textAlign: 'center', width: 50 }}>已执行</th>
                <th style={{ ...th, textAlign: 'center', width: 50 }}>通过</th>
                <th style={{ ...th, textAlign: 'center', width: 56 }}>通过率</th>
                <th style={{ ...th, width: 120 }}>进度</th>
              </tr>
            </thead>
            <tbody>
              {REQ_COVERAGE.map(req => (
                <tr key={req.req_id} style={tr}>
                  <td style={td}><span style={{ fontFamily: "'JetBrains Mono', monospace", color: COLORS.cyan, fontSize: 11 }}>{req.req_id}</span></td>
                  <td style={td}>{req.title}</td>
                  <td style={{ ...td, textAlign: 'center' }}>{req.case_count}</td>
                  <td style={{ ...td, textAlign: 'center' }}>{req.executed_count}</td>
                  <td style={{ ...td, textAlign: 'center' }}>{req.passed_count}</td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    <span style={{ fontWeight: 600, color: PASS_RATE_COLOR(req.pass_rate) }}>{req.pass_rate}%</span>
                  </td>
                  <td style={td}>
                    <div style={{ height: 8, backgroundColor: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden', maxWidth: 100 }}>
                      <div style={{ height: '100%', width: `${req.pass_rate}%`, backgroundColor: PASS_RATE_COLOR(req.pass_rate), borderRadius: 4, transition: 'width 0.4s ease' }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Row 6: Automation + Workflow */}
      <div style={twoCol}>
        <div style={cardSection}>
          <h3 style={cardSectionTitle}>自动化概览</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>框架分布</div>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={Object.entries(AUTOMATION_DATA.framework_dist).map(([k, v]) => ({ name: k, value: v }))}
                    cx="50%" cy="50%" innerRadius={35} outerRadius={60} dataKey="value" label={renderCustomLabel} labelLine={false}>
                    {Object.entries(AUTOMATION_DATA.framework_dist).map(([k], i) => <Cell key={k} fill={FRAMEWORK_COLORS[i]} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              {renderLabelList(Object.entries(AUTOMATION_DATA.framework_dist).map(([k, v]) => ({ name: k, value: v })), FRAMEWORK_COLORS)}
            </div>
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, justifyContent: 'center', height: '100%' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, fontWeight: 700, color: COLORS.cyan }}>{AUTOMATION_DATA.automation_rate}%</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>自动化覆盖率</div>
                </div>
                <div style={miniStatRow}>
                  <MiniStat label="总自动化用例" value={`${AUTOMATION_DATA.total_auto}`} color={COLORS.blue} />
                  <MiniStat label="激活中" value={`${AUTOMATION_DATA.active}`} color={COLORS.green} />
                  <MiniStat label="已弃用" value={`${AUTOMATION_DATA.deprecated}`} color={COLORS.slate} />
                </div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>自动化类型分布</div>
            <ResponsiveContainer width="100%" height={80}>
              <BarChart data={Object.entries(AUTOMATION_DATA.type_dist).map(([k, v]) => ({ name: k, value: v }))} layout="vertical" barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={60} />
                <Bar dataKey="value" name="数量" radius={[0, 4, 4, 0]}>
                  {Object.entries(AUTOMATION_DATA.type_dist).map(([k], i) => <Cell key={k} fill={TYPE_COLORS[i]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div style={cardSection}>
          <h3 style={cardSectionTitle}>工作流状态停留时长</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={WORKFLOW_DATA} layout="vertical" barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-muted)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false}
                label={{ value: '小时', position: 'insideBottom', offset: -4, fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} width={80} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-default)' }}
                formatter={(value, _name, props) => [
                  `${value}h`, `${(props as unknown as { payload: { type: string; count: number } }).payload.type} (${(props as unknown as { payload: { type: string; count: number } }).payload.count} 项)`
                ]}
              />
              <Bar dataKey="avg_hours" name="平均停留" radius={[0, 4, 4, 0]}>
                {WORKFLOW_DATA.map((_, i) => <Cell key={i} fill={WF_COLORS[i % WF_COLORS.length] as string} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>
            颜色 = 事项类型（蓝=需求品红=用例）
          </div>
        </div>
      </div>

      {/* Row 7: Team Performance */}
      <div style={cardSection}>
        <h3 style={cardSectionTitle}>团队效能</h3>
        <div style={tableWrap}>
          <table style={table}>
            <thead>
              <tr>
                <th style={{ ...th, width: 80 }}>用户 ID</th>
                <th style={{ ...th, width: 80 }}>姓名</th>
                <th style={{ ...th, textAlign: 'center' }}>负责用例</th>
                <th style={{ ...th, textAlign: 'center' }}>负责需求</th>
                <th style={{ ...th, textAlign: 'center' }}>创建任务</th>
                <th style={{ ...th, textAlign: 'center' }}>审核用例</th>
                <th style={{ ...th, width: 140 }}>负载条</th>
              </tr>
            </thead>
            <tbody>
              {TEAM_PERFORMANCE.map((u, i) => {
                const maxTasks = Math.max(...TEAM_PERFORMANCE.map(x => x.created_tasks))
                const loadPct = (u.created_tasks / maxTasks) * 100
                return (
                  <tr key={u.user_id} style={{ ...tr, ...(i % 2 === 1 ? { backgroundColor: 'rgba(0,0,0,0.02)' } : {}) }}>
                    <td style={td}><span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: COLORS.purple }}>{u.user_id}</span></td>
                    <td style={td}>{u.username}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.owned_cases}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.owned_reqs}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.created_tasks}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.reviewed_cases}</td>
                    <td style={td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ flex: 1, height: 8, backgroundColor: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${loadPct}%`, backgroundColor: COLORS.cyan, borderRadius: 4, transition: 'width 0.4s ease' }} />
                        </div>
                        <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>{loadPct.toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer: data summary */}
      <div style={cardSection}>
        <h3 style={cardSectionTitle}>数据摘要</h3>
        <div style={summaryGrid}>
          <SummaryBox label="总用例数" value={`${totalCases}`} />
          <SummaryBox label="激活中" value="68" />
          <SummaryBox label="草稿/待审核" value={`${STATUS_DIST.DRAFT + STATUS_DIST.APPROVED}`} />
          <SummaryBox label="已弃用" value={`${STATUS_DIST.DEPRECATED}`} />
          <SummaryBox label="P0 紧急" value={`${PRIORITY_DIST.P0}`} />
          <SummaryBox label="自动化率" value={`${AUTOMATION_DATA.automation_rate}%`} />
          <SummaryBox label="需覆盖需求" value={`${REQ_COVERAGE.length}`} />
          <SummaryBox label="数据截至" value="2026-05-20 11:00" />
        </div>
      </div>
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────

function StatCard({ label, value, color, icon }: { label: string; value: string; color: string; icon: string }) {
  return (
    <div style={statCard}>
      <div style={{ ...statIcon, backgroundColor: `${color}18`, color }}>{icon}</div>
      <div>
        <div style={statLabel}>{label}</div>
        <div style={{ ...statValue, color }}>{value}</div>
      </div>
    </div>
  )
}

function MetricBox({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div style={metricBox}>
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

// ─── Styles ────────────────────────────────────────────────

const pageStyle: React.CSSProperties = {
  padding: 32, maxWidth: 1600, margin: '0 auto',
  animation: 'fadeIn 0.4s ease',
}

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  marginBottom: 24,
}
const titleStyle: React.CSSProperties = {
  fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.5px',
}
const subtitleStyle: React.CSSProperties = {
  fontSize: 14, color: 'var(--text-muted)', margin: '4px 0 0',
}

const rangeGroupStyle: React.CSSProperties = {
  display: 'flex', gap: 4, backgroundColor: 'var(--bg-secondary)',
  padding: 4, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)',
}
const rangeBtn: React.CSSProperties = {
  padding: '8px 16px', fontSize: 13, fontWeight: 500,
  color: 'var(--text-secondary)', backgroundColor: 'transparent',
  border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
  transition: 'all 0.15s ease',
}
const rangeBtnActive: React.CSSProperties = {
  color: 'var(--text-primary)', backgroundColor: 'var(--bg-primary)',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
}

const cardsGrid: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 14, marginBottom: 14,
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
const statLabel: React.CSSProperties = {
  fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.3px',
}
const statValue: React.CSSProperties = {
  fontSize: 22, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.2,
}

const metricsRow: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 14, marginBottom: 14,
}
const metricBox: React.CSSProperties = {
  padding: '16px 20px', backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-default)',
}

const twoCol: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14,
}

const cardSection: React.CSSProperties = {
  backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-default)', padding: 20,
}
const cardSectionTitle: React.CSSProperties = {
  fontSize: 14, fontWeight: 600, color: 'var(--text-primary)',
  margin: '0 0 12px',
}

const tabGroup: React.CSSProperties = {
  display: 'flex', gap: 2, padding: 2,
  backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)',
}
const tabBtn: React.CSSProperties = {
  padding: '5px 12px', fontSize: 11, fontWeight: 500,
  color: 'var(--text-secondary)', backgroundColor: 'transparent',
  border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
  transition: 'all 0.15s ease',
}
const tabBtnActive: React.CSSProperties = {
  color: 'var(--text-primary)', backgroundColor: 'var(--bg-primary)',
  boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
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
