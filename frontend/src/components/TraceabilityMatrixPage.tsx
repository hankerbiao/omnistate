/** 需求追溯矩阵（RTM）页面 — 全局需求-用例覆盖分析与双向追溯 */
import { useState, useEffect, useMemo } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../services/api'
import type { RequirementResponse, TestCaseResponse } from '../types'

/* ── 状态徽标 ── */
const STATUS_DOT: Record<string, string> = {
  COVERED: '#22c55e',
  PARTIAL: '#f59e0b',
  UNCOVERED: '#ef4444',
  EXCESS: '#3b82f6',
}
const STATUS_LABEL: Record<string, string> = {
  COVERED: '已覆盖',
  PARTIAL: '部分覆盖',
  UNCOVERED: '未覆盖',
  EXCESS: '超额覆盖',
}

/** 需求分类标签 */
const CATEGORY_LABELS: Record<string, string> = {
  FUNCTIONAL: '功能',
  PERFORMANCE: '性能',
  STABILITY: '稳定性',
  COMPATIBILITY: '兼容性',
  SECURITY: '安全性',
  REGRESSION: '回归',
}

const CATEGORY_COLORS = ['#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4']
const PRIORITY_ORDER = ['P0', 'P1', 'P2', 'P3']
const PRIORITY_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#9ca3af']

/* ── 工具函数 ── */
function getCoverageStatus(linkedCount: number): string {
  if (linkedCount === 0) return 'UNCOVERED'
  if (linkedCount === 1) return 'COVERED'
  return 'EXCESS'
}

export default function TraceabilityMatrixPage() {
  const [requirements, setRequirements] = useState<RequirementResponse[]>([])
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedReqId, setExpandedReqId] = useState<string | null>(null)
  const [showUnlinked, setShowUnlinked] = useState(false)
  const [showUncovered, setShowUncovered] = useState(false)

  /* ── 数据获取 ── */
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      api.listRequirements({ limit: 200 }),
      api.listTestCases({ limit: 200 }),
    ]).then(([reqRes, tcRes]) => {
      if (cancelled) return
      setRequirements(reqRes.data || [])
      setTestCases(tcRes.data || [])
    }).catch(() => {
      if (cancelled) return
      setRequirements([])
      setTestCases([])
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  /* ── 计算覆盖关系: req_id → TestCase[] ── */
  const caseMapByReq = useMemo(() => {
    const map = new Map<string, TestCaseResponse[]>()
    for (const tc of testCases) {
      if (!tc.ref_req_id) continue
      const list = map.get(tc.ref_req_id) || []
      list.push(tc)
      map.set(tc.ref_req_id, list)
    }
    return map
  }, [testCases])

  /* ── 覆盖率统计 ── */
  const coverageStats = useMemo(() => {
    const total = requirements.length
    let covered = 0, uncovered = 0, excess = 0
    const byCategory: Record<string, { total: number; covered: number }> = {}
    const byPriority: Record<string, { total: number; covered: number }> = {}

    for (const req of requirements) {
      const linked = caseMapByReq.get(req.req_id)?.length || 0
      const status = getCoverageStatus(linked)
      if (status === 'COVERED' || status === 'EXCESS') covered++
      if (status === 'UNCOVERED') uncovered++
      if (status === 'EXCESS') excess++

      // By category
      const cat = req.category || '其他'
      if (!byCategory[cat]) byCategory[cat] = { total: 0, covered: 0 }
      byCategory[cat].total++
      if (status !== 'UNCOVERED') byCategory[cat].covered++

      // By priority
      const pri = req.priority
      if (!byPriority[pri]) byPriority[pri] = { total: 0, covered: 0 }
      byPriority[pri].total++
      if (status !== 'UNCOVERED') byPriority[pri].covered++
    }

    const coverageRate = total > 0 ? Math.round((covered / total) * 100) : 0
    return { total, covered, uncovered, excess, coverageRate, byCategory, byPriority }
  }, [requirements, caseMapByReq])

  /* ── Pie data for coverage status ── */
  const statusPieData = useMemo(() => {
    const items = [
      { name: '已覆盖', value: coverageStats.covered - coverageStats.excess, fill: '#22c55e' },
      { name: '超额覆盖', value: coverageStats.excess, fill: '#3b82f6' },
      { name: '未覆盖', value: coverageStats.uncovered, fill: '#ef4444' },
    ]
    return items.filter(i => i.value > 0)
  }, [coverageStats])

  /* ── 未覆盖需求列表 ── */
  const uncoveredReqs = useMemo(() => {
    return requirements.filter(req => {
      const linked = caseMapByReq.get(req.req_id)?.length || 0
      return linked === 0
    })
  }, [requirements, caseMapByReq])

  /* ── 未关联用例列表 ── */
  const unlinkedCases = useMemo(() => {
    return testCases.filter(tc => !tc.ref_req_id)
  }, [testCases])

  /* ── 带覆盖标记的需求列表 ── */
  const reqRows = useMemo(() => {
    return requirements.map(req => {
      const linked = caseMapByReq.get(req.req_id) || []
      const status = getCoverageStatus(linked.length)
      return { req, linked, status }
    })
  }, [requirements, caseMapByReq])

  /* ── Loading ── */
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-tertiary)' }}>
        加载中...
      </div>
    )
  }

  return (
    <div style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      {/* ── Coverage Overview Cards ── */}
      <div className="dashboard-metric-grid">
        <div className="stat-card">
          <span className="stat-card__label">需求总数</span>
          <span className="stat-card__value">{coverageStats.total}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">已覆盖需求</span>
          <span className="stat-card__value" style={{ color: '#22c55e' }}>{coverageStats.covered}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__label">未覆盖需求</span>
          <span className="stat-card__value" style={{ color: coverageStats.uncovered > 0 ? '#ef4444' : 'inherit' }}>{coverageStats.uncovered}</span>
          {coverageStats.uncovered > 0 && (
            <button
              onClick={() => setShowUncovered(!showUncovered)}
              style={{ fontSize: 11, color: 'var(--accent-primary)', cursor: 'pointer', background: 'none', border: 'none', padding: 0, marginTop: 4, textAlign: 'left' }}
            >查看详情 &rarr;</button>
          )}
        </div>
        <div className="stat-card">
          <span className="stat-card__label">覆盖率</span>
          <span className="stat-card__value">{coverageStats.coverageRate}%</span>
          <span className="stat-card__delta" style={{ color: coverageStats.coverageRate >= 80 ? '#16a34a' : coverageStats.coverageRate >= 50 ? '#ca8a04' : '#dc2626' }}>
            {coverageStats.coverageRate >= 80 ? '良好' : coverageStats.coverageRate >= 50 ? '一般' : '偏低'}
          </span>
        </div>
      </div>

      {/* ── Uncovered Requirements Detail ── */}
      {showUncovered && uncoveredReqs.length > 0 && (
        <div style={{ marginTop: 16, padding: 16, background: '#fef2f2', borderRadius: 10, border: '1px solid #fecaca' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#dc2626', marginBottom: 12 }}>
            未覆盖需求 ({uncoveredReqs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {uncoveredReqs.map(req => (
              <div key={req.req_id} style={{ fontSize: 13, padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #fecaca' }}>
                <span style={{ fontWeight: 500 }}>{req.req_id}</span>
                {' - '}
                <span style={{ color: 'var(--text-secondary)' }}>{req.title}</span>
                <span style={{ float: 'right', fontSize: 11, color: '#dc2626', fontWeight: 600 }}>{CATEGORY_LABELS[req.category || ''] || req.category} / {req.priority}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Charts Row ── */}
      <div className="dashboard-chart-grid" style={{ marginTop: 20 }}>
        {/* 覆盖率饼图 */}
        <div className="chart-card">
          <div className="chart-card__title">覆盖状态分布</div>
          <div style={{ height: 220 }}>
            {statusPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={statusPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                    {statusPieData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend formatter={(value: string) => <span style={{ fontSize: 12, color: '#374151' }}>{value}</span>} />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty />}
          </div>
        </div>

        {/* 按分类覆盖率柱状图 */}
        <div className="chart-card">
          <div className="chart-card__title">按需求分类覆盖率</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Object.entries(coverageStats.byCategory)
                .filter(([cat]) => cat !== '其他')
                .concat(Object.entries(coverageStats.byCategory).filter(([cat]) => cat === '其他'))
                .map(([cat, stats]) => ({
                  name: CATEGORY_LABELS[cat] || cat,
                  总数: stats.total,
                  已覆盖: stats.covered,
                  fill: CATEGORY_COLORS[Object.keys(CATEGORY_LABELS).indexOf(cat)] || '#94a3b8',
                }))}
                layout="vertical" barGap={0} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={60} />
                <Tooltip />
                <Bar dataKey="总数" stackId="a" fill="#e5e7eb" />
                <Bar dataKey="已覆盖" stackId="a" fill="#22c55e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 按优先级覆盖率柱状图 */}
        <div className="chart-card">
          <div className="chart-card__title">按优先级覆盖率</div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={PRIORITY_ORDER
                .filter(p => coverageStats.byPriority[p])
                .map(p => ({
                  name: p,
                  总数: coverageStats.byPriority[p].total,
                  已覆盖: coverageStats.byPriority[p].covered,
                }))}
                layout="vertical" barGap={0} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={40} />
                <Tooltip />
                <Bar dataKey="总数" stackId="a" fill="#e5e7eb" />
                <Bar dataKey="已覆盖" stackId="a" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Full Traceability Table ── */}
      <div className="surface-card" style={{ marginTop: 20 }}>
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>需求覆盖明细</span>
          <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
            {reqRows.filter(r => r.status !== 'UNCOVERED').length}/{reqRows.length} 已覆盖
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-subtle)', background: 'var(--surface-tertiary)' }}>
                <th style={thStyle}>ID</th>
                <th style={thStyle}>标题</th>
                <th style={thStyle}>分类</th>
                <th style={thStyle}>优先级</th>
                <th style={thStyle}>覆盖状态</th>
                <th style={thStyle}>用例数</th>
                <th style={thStyle}>负责人</th>
                <th style={{ ...thStyle, width: 80 }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {reqRows.map(({ req, linked, status }) => {
                const isExpanded = expandedReqId === req.req_id
                return (
                  <>
                    <tr
                      key={req.req_id}
                      onClick={() => setExpandedReqId(isExpanded ? null : req.req_id)}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        cursor: 'pointer',
                        background: isExpanded ? 'var(--surface-hover)' : undefined,
                      }}
                    >
                      <td style={tdStyle}><code style={{ fontSize: 12 }}>{req.req_id}</code></td>
                      <td style={{ ...tdStyle, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {req.title}
                      </td>
                      <td style={tdStyle}>
                        <span style={tagStyle(CATEGORY_COLORS[Object.keys(CATEGORY_LABELS).indexOf(req.category || '')] || '#94a3b8')}>
                          {CATEGORY_LABELS[req.category || ''] || req.category}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <span style={prioStyle(req.priority)}>{req.priority}</span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: STATUS_DOT[status] }} />
                          <span style={{ fontSize: 12, color: STATUS_DOT[status], fontWeight: 500 }}>{STATUS_LABEL[status]}</span>
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 600, color: status === 'UNCOVERED' ? '#ef4444' : 'var(--text-primary)' }}>
                          {linked.length}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, color: 'var(--text-secondary)', fontSize: 12 }}>{req.tpm_owner_name || '-'}</td>
                      <td style={tdStyle}>
                        <span style={{ fontSize: 11, color: 'var(--accent-primary)' }}>
                          {isExpanded ? '收起' : '展开'}
                        </span>
                      </td>
                    </tr>
                    {/* Expanded detail: linked test cases */}
                    {isExpanded && (
                      <tr key={`${req.req_id}-detail`}>
                        <td colSpan={8} style={{ padding: 0, borderBottom: '1px solid var(--border-subtle)' }}>
                          {linked.length > 0 ? (
                            <div style={{ padding: '8px 16px 12px 40px', background: 'var(--surface-secondary)' }}>
                              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                                关联测试用例：
                              </div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {linked.map(tc => (
                                  <div key={tc.case_id} style={{
                                    display: 'flex', alignItems: 'center', gap: 8,
                                    padding: '6px 10px', background: '#fff', borderRadius: 6,
                                    border: '1px solid var(--border-subtle)', fontSize: 12,
                                  }}>
                                    <code style={{ fontSize: 11, color: 'var(--accent-primary)', fontWeight: 500 }}>{tc.case_id}</code>
                                    <span style={{ flex: 1, color: 'var(--text-primary)' }}>{tc.title}</span>
                                    <span style={tagStyle(tc.priority === 'P0' ? '#ef4444' : tc.priority === 'P1' ? '#f59e0b' : '#6b7280')}>
                                      {tc.priority || '-'}
                                    </span>
                                    <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>
                                      {tc.lab_name || tc.lab_id || ''}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div style={{ padding: '8px 16px 12px 40px', background: '#fef2f2', fontSize: 12, color: '#dc2626' }}>
                              暂无关联用例 — 请在创建或编辑测试用例时指定关联需求
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Unlinked Test Cases ── */}
      {unlinkedCases.length > 0 && (
        <div className="surface-card" style={{ marginTop: 16 }}>
          <div
            onClick={() => setShowUnlinked(!showUnlinked)}
            style={{
              padding: '12px 16px', borderBottom: showUnlinked ? '1px solid var(--border-subtle)' : 'none',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              cursor: 'pointer', userSelect: 'none',
            }}
          >
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              <span style={{ color: '#f59e0b' }}>⚠</span> 未关联需求的用例
              <span style={{ fontWeight: 400, fontSize: 12, color: 'var(--text-tertiary)', marginLeft: 8 }}>{unlinkedCases.length} 个</span>
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{showUnlinked ? '收起' : '展开'}</span>
          </div>
          {showUnlinked && (
            <div style={{ padding: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {unlinkedCases.slice(0, 30).map(tc => (
                  <div key={tc.case_id} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 10px', fontSize: 12,
                    borderBottom: '1px solid var(--border-subtle)',
                  }}>
                    <code style={{ fontSize: 11, color: '#f59e0b', fontWeight: 500 }}>{tc.case_id}</code>
                    <span style={{ flex: 1 }}>{tc.title}</span>
                    <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>{tc.lab_name || tc.lab_id || ''}</span>
                  </div>
                ))}
                {unlinkedCases.length > 30 && (
                  <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-tertiary)', padding: 8 }}>
                    还有 {unlinkedCases.length - 30} 个...
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Shared inline styles ── */
const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '10px 12px', fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)',
  whiteSpace: 'nowrap',
}
const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
}
const tagStyle = (color: string): React.CSSProperties => ({
  display: 'inline-block',
  padding: '1px 8px',
  borderRadius: 10,
  fontSize: 11,
  fontWeight: 500,
  background: `${color}18`,
  color,
  border: `1px solid ${color}30`,
})
const prioStyle = (pri: string): React.CSSProperties => {
  const colors: Record<string, string> = { P0: '#dc2626', P1: '#f59e0b', P2: '#3b82f6', P3: '#9ca3af' }
  const c = colors[pri] || '#6b7280'
  return {
    display: 'inline-block', padding: '1px 8px', borderRadius: 10, fontSize: 11,
    fontWeight: 600, background: `${c}18`, color: c,
  }
}
function Empty() {
  return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#9ca3af', fontSize: 13 }}>暂无数据</div>
}
