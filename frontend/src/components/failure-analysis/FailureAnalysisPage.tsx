/** 失效分析仪表盘页面 */
import { useState, useEffect, useMemo } from 'react'
import {
  PieChart, Pie, Cell, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import PageToolbar, { StatPill } from '../ui/PageToolbar'
import { getCatalogLabs } from '../../services/catalogLabsCache'
import { getFailureAnalysisMockData } from './failureAnalysisMockData'
import type { FailureAnalysisDashboard, FailurePattern, CatalogLab } from '../../types'

const PATTERN_COLORS: Record<string, string> = {
  TIMEOUT: '#f59e0b',
  ASSERTION_ERROR: '#ef4444',
  ENV_SETUP: '#8b5cf6',
  DEPENDENCY: '#f97316',
  CONFIG_ERROR: '#ec4899',
  NETWORK_ERROR: '#06b6d4',
  HARDWARE_ERROR: '#64748b',
  MEMORY_ERROR: '#a855f7',
  SCRIPT_ERROR: '#3b82f6',
  UNKNOWN: '#94a3b8',
}

const PATTERN_LABELS: Record<string, string> = {
  TIMEOUT: '超时',
  ASSERTION_ERROR: '断言失败',
  ENV_SETUP: '环境异常',
  DEPENDENCY: '依赖缺失',
  CONFIG_ERROR: '配置错误',
  NETWORK_ERROR: '网络异常',
  HARDWARE_ERROR: '硬件异常',
  MEMORY_ERROR: '内存错误',
  SCRIPT_ERROR: '脚本错误',
  UNKNOWN: '未识别',
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'PASSED' ? '#22c55e' : status === 'FAILED' ? '#ef4444' : '#6b7280'
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: color, marginRight: 4 }} />
}

export default function FailureAnalysisPage() {
  const [data, setData] = useState<FailureAnalysisDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('30d')
  const [labs, setLabs] = useState<CatalogLab[]>([])
  const [selectedLabId, setSelectedLabId] = useState('all')

  // ── Load labs ──
  useEffect(() => {
    getCatalogLabs({ active_only: true }).then(items => {
      setLabs(items)
    }).catch(() => {})
  }, [])

  // ── Generate mock data ──
  useEffect(() => {
    setLoading(true)
    const timer = setTimeout(() => {
      setData(getFailureAnalysisMockData(timeRange, selectedLabId))
      setLoading(false)
    }, 400)
    return () => clearTimeout(timer)
  }, [timeRange, selectedLabId])

  const pieData = useMemo(() => {
    if (!data) return []
    return data.pattern_distribution.map(d => ({
      name: PATTERN_LABELS[d.pattern] || d.pattern,
      value: d.count,
      fill: PATTERN_COLORS[d.pattern],
    }))
  }, [data])

  const stackedChartData = useMemo(() => {
    if (!data) return []
    const allPatterns = new Set<string>()
    data.daily_trend.forEach(d => Object.keys(d.patterns).forEach(p => allPatterns.add(p)))
    const patterns = Array.from(allPatterns)

    return data.daily_trend.map(d => {
      const item: Record<string, string | number> = { date: d.date.slice(5) }
      patterns.forEach(p => { item[p] = d.patterns[p] || 0 })
      return item
    })
  }, [data])

  const rangeOptions = [
    { value: '7d', label: '7 天' },
    { value: '30d', label: '30 天' },
    { value: '90d', label: '90 天' },
  ]

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>加载中...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>暂无数据</div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <PageToolbar
        meta={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <StatPill label="总失败数" value={data.total_failures} {...(data.total_failures > 50 ? { tone: 'danger' } : {})} />
            <StatPill label="不稳定测试" value={data.flaky_tests.length} tone="warning" />
            <StatPill label="高频失败" value={data.high_frequency_failures.length} tone="info" />
          </div>
        }
        actions={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* 项目选择 */}
            <select
              value={selectedLabId}
              onChange={e => setSelectedLabId(e.target.value)}
              className="form-input form-select"
              style={{ width: 180, fontSize: 12 }}
            >
              <option value="all">全部项目</option>
              {labs.map(lab => (
                <option key={lab.lab_id} value={lab.lab_id}>{lab.name}</option>
              ))}
            </select>
            {/* 时间范围 */}
            <div style={{ display: 'flex', gap: 4 }}>
              {rangeOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setTimeRange(opt.value)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 6,
                    border: `1px solid ${timeRange === opt.value ? '#2563eb' : '#d1d5db'}`,
                    background: timeRange === opt.value ? '#dbeafe' : '#fff',
                    color: timeRange === opt.value ? '#2563eb' : '#374151',
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >{opt.label}</button>
              ))}
            </div>
          </div>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginTop: 16 }}>
        {/* 失败模式分布饼图 */}
        <SectionCard title="失败模式分布">
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Legend formatter={(value: string) => <span style={{ fontSize: 12, color: '#374151' }}>{value}</span>} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyPlaceholder />
          )}
        </SectionCard>

        {/* 每日趋势堆叠柱状图 */}
        <SectionCard title="失败趋势（按天）">
          {stackedChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stackedChartData} barGap={0} barCategoryGap="10%">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                {Object.keys(PATTERN_COLORS).map(p => (
                  <Bar key={p} dataKey={p} stackId="a" fill={PATTERN_COLORS[p]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyPlaceholder />
          )}
        </SectionCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
        {/* 按代理分布 */}
        <SectionCard title="按执行代理分布">
          {data.by_agent.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {data.by_agent.map(agent => (
                <div key={agent.agent_id} style={{ padding: '10px 12px', background: '#f8fafc', borderRadius: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontWeight: 500, fontSize: 13 }}>{agent.hostname}</span>
                    <span style={{ fontSize: 12, color: '#6b7280' }}>{agent.failure_count} 次失败</span>
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {Object.entries(agent.pattern_breakdown).map(([pattern, count]) => (
                      <span key={pattern} style={{
                        padding: '2px 8px',
                        borderRadius: 10,
                        fontSize: 11,
                        background: `${PATTERN_COLORS[pattern]}20`,
                        color: PATTERN_COLORS[pattern],
                        border: `1px solid ${PATTERN_COLORS[pattern]}40`,
                      }}>{PATTERN_LABELS[pattern] || pattern}: {count}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyPlaceholder />
          )}
        </SectionCard>

        {/* 不稳定测试 */}
        <SectionCard title={`不稳定测试（${data.flaky_tests.length} 个）`}>
          {data.flaky_tests.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {data.flaky_tests.slice(0, 10).map(test => (
                <div key={test.auto_case_id} style={{
                  padding: '8px 12px',
                  background: '#f8fafc',
                  borderRadius: 6,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{test.name}</div>
                    <div style={{ fontSize: 11, color: '#6b7280' }}>总运行 {test.total_runs} 次</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ display: 'flex', gap: 2 }}>
                      {test.recent_results.slice(0, 10).map((r, i) => (
                        <StatusDot key={i} status={r.status as string} />
                      ))}
                    </div>
                    <span style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: test.flaky_ratio > 0.3 ? '#ef4444' : test.flaky_ratio > 0.15 ? '#f59e0b' : '#22c55e',
                    }}>{(test.flaky_ratio * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyPlaceholder />
          )}
        </SectionCard>
      </div>

      {/* 高频失败 */}
      <SectionCard title={`高频失败 Top ${data.high_frequency_failures.length}`} style={{ marginTop: 16 }}>
        {data.high_frequency_failures.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 500 }}>名称</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 500 }}>失败次数</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 500 }}>主导模式</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#6b7280', fontWeight: 500 }}>最近失败</th>
              </tr>
            </thead>
            <tbody>
              {data.high_frequency_failures.map(f => (
                <tr key={f.auto_case_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '8px 12px', fontWeight: 500 }}>{f.name}</td>
                  <td style={{ padding: '8px 12px' }}>{f.failure_count}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: 10,
                      fontSize: 11,
                      background: `${PATTERN_COLORS[f.dominant_pattern]}20`,
                      color: PATTERN_COLORS[f.dominant_pattern],
                    }}>{PATTERN_LABELS[f.dominant_pattern] || f.dominant_pattern}</span>
                  </td>
                  <td style={{ padding: '8px 12px', color: '#6b7280', fontSize: 12 }}>
                    {f.latest_failure_at ? new Date(f.latest_failure_at).toLocaleDateString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyPlaceholder />
        )}
      </SectionCard>
    </div>
  )
}

function SectionCard({ title, children, style }: { title: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: '#fff',
      borderRadius: 10,
      border: '1px solid #e5e7eb',
      overflow: 'hidden',
      ...style,
    }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #e5e7eb',
        fontWeight: 600,
        fontSize: 14,
        color: '#111827',
      }}>{title}</div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  )
}

function EmptyPlaceholder() {
  return (
    <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af', fontSize: 13 }}>暂无数据</div>
  )
}
