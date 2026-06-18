// ═══════════════════════════════════════════════════════════════════════
//  ProjectsPage — 项目管理页面
//   分栏布局：左侧项目列表 + 右侧项目详情（各数据模块点击查看详情）
// ═══════════════════════════════════════════════════════════════════════

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigation } from '../providers/NavigationProvider'
import { api } from '../services/api'
import type { Project, ProjectDetail, ProjectStats, AssigneeDistribution } from '../types'

// ── Mock 数据类型 ──────────────────────────────────────────────────────

interface MockTask {
  id: string; name: string; assignee: string; status: string; progress: number; priority: string; updated: string
}

interface MockCase {
  id: string; title: string; module: string; status: string; priority: string; executor: string; lastResult: string
}

interface MockPlan {
  id: string; name: string; status: string; total: number; passed: number; failed: number; executor: string; date: string
}

interface MockRequirement {
  id: string; title: string; priority: string; status: string; caseCount: number; coverageRate: number; owner: string
}

interface MockActivity {
  id: string; time: string; user: string; action: string; target: string; type: string
}

// ── Mock 数据 ─────────────────────────────────────────────────────────

const mockTasks: MockTask[] = [
  { id: 'T-001', name: '登录模块功能验证', assignee: '张三', status: '已完成', progress: 100, priority: 'P0', updated: '2024-03-15' },
  { id: 'T-002', name: '权限管理回归测试', assignee: '李四', status: '进行中', progress: 65, priority: 'P1', updated: '2024-03-14' },
  { id: 'T-003', name: '数据导出性能测试', assignee: '王五', status: '进行中', progress: 30, priority: 'P1', updated: '2024-03-13' },
  { id: 'T-004', name: 'UI兼容性适配验证', assignee: '赵六', status: '失败', progress: 45, priority: 'P2', updated: '2024-03-12' },
  { id: 'T-005', name: '接口安全扫描', assignee: '张三', status: '待执行', progress: 0, priority: 'P0', updated: '2024-03-11' },
  { id: 'T-006', name: '批量导入功能测试', assignee: '李四', status: '待执行', progress: 0, priority: 'P2', updated: '2024-03-10' },
  { id: 'T-007', name: '消息通知推送验证', assignee: '王五', status: '已完成', progress: 100, priority: 'P1', updated: '2024-03-09' },
  { id: 'T-008', name: '搜索功能准确率测试', assignee: '赵六', status: '进行中', progress: 80, priority: 'P2', updated: '2024-03-08' },
]

const mockManualCases: MockCase[] = [
  { id: 'MC-001', title: '用户登录-正常流程', module: '登录', status: '通过', priority: 'P0', executor: '张三', lastResult: '通过' },
  { id: 'MC-002', title: '用户登录-密码错误', module: '登录', status: '通过', priority: 'P0', executor: '张三', lastResult: '通过' },
  { id: 'MC-003', title: '权限分配-管理员', module: '权限', status: '通过', priority: 'P1', executor: '李四', lastResult: '通过' },
  { id: 'MC-004', title: '权限分配-只读用户', module: '权限', status: '失败', priority: 'P1', executor: '李四', lastResult: '失败' },
  { id: 'MC-005', title: '数据导出-CSV格式', module: '数据', status: '通过', priority: 'P2', executor: '王五', lastResult: '通过' },
  { id: 'MC-006', title: '数据导出-Excel格式', module: '数据', status: '阻塞', priority: 'P2', executor: '王五', lastResult: '未执行' },
  { id: 'MC-007', title: 'UI-深色模式显示', module: 'UI', status: '通过', priority: 'P2', executor: '赵六', lastResult: '通过' },
  { id: 'MC-008', title: 'UI-移动端适配', module: 'UI', status: '进行中', priority: 'P1', executor: '赵六', lastResult: '未执行' },
]

const mockAutoCases: MockCase[] = [
  { id: 'AC-001', title: '[自动] 登录接口测试', module: 'API', status: '通过', priority: 'P0', executor: 'CI', lastResult: '通过' },
  { id: 'AC-002', title: '[自动] 用户注册校验', module: 'API', status: '通过', priority: 'P0', executor: 'CI', lastResult: '通过' },
  { id: 'AC-003', title: '[自动] 权限拦截测试', module: 'API', status: '失败', priority: 'P1', executor: 'CI', lastResult: '失败' },
  { id: 'AC-004', title: '[自动] 数据一致性检查', module: '数据', status: '通过', priority: 'P1', executor: 'CI', lastResult: '通过' },
  { id: 'AC-005', title: '[自动] 超时处理测试', module: 'API', status: '通过', priority: 'P2', executor: 'CI', lastResult: '通过' },
  { id: 'AC-006', title: '[自动] 并发请求测试', module: '性能', status: '失败', priority: 'P1', executor: 'CI', lastResult: '失败' },
]

const mockPlans: MockPlan[] = [
  { id: 'P-001', name: 'V2.0 回归测试计划', status: '已完成', total: 120, passed: 108, failed: 12, executor: '张三', date: '2024-03-01 ~ 2024-03-10' },
  { id: 'P-002', name: 'V2.1 冒烟测试', status: '进行中', total: 45, passed: 32, failed: 3, executor: '李四', date: '2024-03-11 ~ 2024-03-15' },
  { id: 'P-003', name: '安全专项扫描', status: '待执行', total: 60, passed: 0, failed: 0, executor: '王五', date: '2024-03-20 ~ 2024-03-25' },
]

const mockRequirements: MockRequirement[] = [
  { id: 'R-001', title: '用户登录功能', priority: 'P0', status: '已覆盖', caseCount: 8, coverageRate: 100, owner: '张三' },
  { id: 'R-002', title: '权限分级管理', priority: 'P0', status: '已覆盖', caseCount: 12, coverageRate: 100, owner: '李四' },
  { id: 'R-003', title: '数据导出功能', priority: 'P1', status: '部分覆盖', caseCount: 5, coverageRate: 62, owner: '王五' },
  { id: 'R-004', title: '深色模式适配', priority: 'P2', status: '部分覆盖', caseCount: 3, coverageRate: 50, owner: '赵六' },
  { id: 'R-005', title: '消息实时推送', priority: 'P1', status: '未覆盖', caseCount: 0, coverageRate: 0, owner: '张三' },
]

const mockActivities: MockActivity[] = [
  { id: 'A-01', time: '刚刚', user: '张三', action: '完成', target: '登录模块功能验证', type: 'task_done' },
  { id: 'A-02', time: '5分钟前', user: '李四', action: '标记进行中', target: '权限管理回归测试', type: 'task_running' },
  { id: 'A-03', time: '1小时前', user: '王五', action: '创建计划', target: '安全专项扫描', type: 'plan_create' },
  { id: 'A-04', time: '2小时前', user: '赵六', action: '提交用例', target: 'UI-深色模式显示', type: 'case_pass' },
  { id: 'A-05', time: '3小时前', user: '张三', action: '标记失败', target: '接口安全扫描', type: 'task_fail' },
  { id: 'A-06', time: '昨天', user: '李四', action: '归档计划', target: 'V2.0 回归测试计划', type: 'plan_done' },
]

const mockBlockers = [
  { id: 'T-004', name: 'UI兼容性适配验证', type: '失败', assignee: '赵六', color: '#f85149' },
  { id: 'T-005', name: '接口安全扫描', type: '待执行(P0)', assignee: '张三', color: '#f85149' },
  { id: 'MC-004', name: '权限分配-只读用户', type: '失败', assignee: '李四', color: '#f85149' },
  { id: 'AC-003', name: '[自动] 权限拦截测试', type: '失败', assignee: 'CI', color: '#f85149' },
]

// ── 样式 ─────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  wrapper: { height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  toolbar: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 },
  workspace: { flex: 1, display: 'flex', overflow: 'hidden' },
  sidePanel: { width: 280, borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 },
  mainPanel: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  scroll: { flex: 1, overflowY: 'auto', padding: '8px 0' },
  detailScroll: { flex: 1, overflowY: 'auto', padding: '16px 20px' },
  statCard: { background: 'var(--surface-secondary)', borderRadius: 6, padding: '10px 8px', textAlign: 'center', flex: 1, minWidth: 0 },
  statValue: { fontSize: 18, fontWeight: 700, color: 'var(--accent-primary)', lineHeight: 1.1 },
  statLabel: { fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 },
  progressBar: { height: 6, borderRadius: 3, background: 'var(--surface-tertiary)', overflow: 'hidden', marginTop: 4 },
  progressFill: (pct: number, color: string) => ({ width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }),
  pill: (bg: string, fg: string) => ({ display: 'inline-block', fontSize: 9, padding: '1px 6px', borderRadius: 7, background: bg, color: fg, fontWeight: 600 }),
  modalOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: 'var(--surface-primary)', borderRadius: 12, width: 680, maxWidth: '90vw', maxHeight: '85vh', overflowY: 'auto', padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' },
  clickable: { cursor: 'pointer', transition: 'all 0.12s' },
  clickIcon: { fontSize: 10, color: 'var(--text-tertiary)', marginLeft: 6, opacity: 0.6 },
}

// ── helpers ───────────────────────────────────────────────────────────

function fmtDate(d: string | null | undefined): string {
  if (!d) return '-'
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return d }
}

function pctStr(v: number): string { return `${v}%` }

const PRIORITY: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: '#f85149' }, P1: { label: 'P1', color: '#d29922' }, P2: { label: 'P2', color: '#8b949e' },
}
const STATUS: Record<string, { label: string; color: string }> = {
  active: { label: '活跃', color: '#3fb950' }, archived: { label: '已归档', color: '#8b949e' },
}

// ── Mock Stats（API 返回空时使用） ────────────────────────────────────

const MOCK_STATS: ProjectStats = {
  test_case_count: 36,
  auto_case_count: 18,
  requirement_count: 8,
  plan_count: 5,
  collection_count: 4,
  task: { total: 20, done: 9, running: 4, failed: 2, pending: 5, progress: 45 },
  task_progress: 45,
  manual_pass: { total: 36, passed: 28, failed: 5, pass_rate: 78 },
  auto_pass: { total: 18, passed: 14, failed: 4, pass_rate: 78 },
  coverage_rate: 72,
  assignee_distribution: [
    { assignee_id: 'u001', assignee_name: '张三', item_count: 6, done_count: 3, progress: 50 },
    { assignee_id: 'u002', assignee_name: '李四', item_count: 5, done_count: 2, progress: 40 },
    { assignee_id: 'u003', assignee_name: '王五', item_count: 5, done_count: 2, progress: 40 },
    { assignee_id: 'u004', assignee_name: '赵六', item_count: 4, done_count: 2, progress: 50 },
  ],
}

function useStats(raw: ProjectStats | null | undefined): ProjectStats | null {
  return useMemo(() => {
    if (!raw) return MOCK_STATS
    // 如果 API 返回全是 0，也降级到 mock
    const s = raw
    if (!s.task?.total && !s.manual_pass?.total && !s.auto_case_count && !s.test_case_count) {
      return MOCK_STATS
    }
    return s
  }, [raw])
}

// ── 通用组件：弹窗详情 ────────────────────────────────────────────────

function DetailModal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div style={s.modalOverlay} onClick={onClose}>
      <div style={{ ...s.modal, width: 760 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <span style={{ fontSize: 16, fontWeight: 700 }}>{title}</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--text-tertiary)' }}>×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function SectionHeader({ title, onClick }: { title: string; onClick?: () => void }) {
  return (
    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <span>{title}</span>
      {onClick && <span style={{ ...s.clickIcon, marginLeft: 8 }}>→ 查看详情</span>}
    </div>
  )
}

// ── Mock详情弹窗内容 ──────────────────────────────────────────────────

function TaskDetailTable({ tasks }: { tasks: MockTask[] }) {
  const rowStyle = (status: string): React.CSSProperties => ({
    padding: '8px 10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 80px', gap: 8, alignItems: 'center',
  })
  const statusPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已完成': ['#3fb950', '#3fb95022'], '进行中': ['#d29922', '#d2992222'], '失败': ['#f85149', '#f8514922'], '待执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']
    return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle(''), fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>任务名称</span><span>负责人</span><span>进度</span><span>优先级</span><span>状态</span>
      </div>
      {tasks.map(t => (
        <div key={t.id} style={rowStyle(t.status)}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{t.id}</span>
          <span style={{ fontWeight: 500 }}>{t.name}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{t.assignee}</span>
          <span>{pctStr(t.progress)}</span>
          <span style={s.pill(PRIORITY[t.priority]?.color + '22' || '#8b949e22', PRIORITY[t.priority]?.color || '#8b949e')}>{t.priority}</span>
          <span>{statusPill(t.status)}</span>
        </div>
      ))}
    </div>
  )
}

function CaseDetailTable({ cases, type }: { cases: MockCase[]; type: string }) {
  const rowStyle: React.CSSProperties = { padding: '8px 10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '90px 1fr 70px 60px 60px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '通过': ['#3fb950', '#3fb95022'], '失败': ['#f85149', '#f8514922'], '阻塞': ['#8b949e', '#8b949e22'], '进行中': ['#d29922', '#d2992222'], '未执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']
    return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>用例名称</span><span>模块</span><span>优先级</span><span>结果</span>
      </div>
      {cases.map(c => (
        <div key={c.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{c.id}</span>
          <span style={{ fontWeight: 500 }}>{c.title}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{c.module}</span>
          <span style={s.pill(PRIORITY[c.priority]?.color + '22' || '#8b949e22', PRIORITY[c.priority]?.color || '#8b949e')}>{c.priority}</span>
          <span>{stPill(c.lastResult)}</span>
        </div>
      ))}
    </div>
  )
}

function PlanDetailTable({ plans }: { plans: MockPlan[] }) {
  const rowStyle: React.CSSProperties = { padding: '10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 80px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已完成': ['#3fb950', '#3fb95022'], '进行中': ['#d29922', '#d2992222'], '待执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>计划名称</span><span>状态</span><span>通过率</span><span>执行人</span><span>周期</span>
      </div>
      {plans.map(p => (
        <div key={p.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{p.id}</span>
          <span style={{ fontWeight: 500 }}>{p.name}</span>
          <span>{stPill(p.status)}</span>
          <span style={{ fontWeight: 600, color: p.passed / p.total > 0.8 ? '#3fb950' : '#d29922' }}>{pctStr(Math.round(p.passed / p.total * 100))}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{p.executor}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{p.date}</span>
        </div>
      ))}
    </div>
  )
}

function ReqDetailTable({ reqs }: { reqs: MockRequirement[] }) {
  const rowStyle: React.CSSProperties = { padding: '10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 60px 80px 60px 70px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已覆盖': ['#3fb950', '#3fb95022'], '部分覆盖': ['#d29922', '#d2992222'], '未覆盖': ['#f85149', '#f8514922'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>需求名称</span><span>优先级</span><span>覆盖状态</span><span>用例数</span><span>覆盖率</span>
      </div>
      {reqs.map(r => (
        <div key={r.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{r.id}</span>
          <span style={{ fontWeight: 500 }}>{r.title}</span>
          <span style={s.pill(PRIORITY[r.priority]?.color + '22' || '#8b949e22', PRIORITY[r.priority]?.color || '#8b949e')}>{r.priority}</span>
          <span>{stPill(r.status)}</span>
          <span>{r.caseCount}</span>
          <span style={{ fontWeight: 600, color: r.coverageRate >= 80 ? '#3fb950' : r.coverageRate >= 50 ? '#d29922' : '#f85149' }}>{pctStr(r.coverageRate)}</span>
        </div>
      ))}
    </div>
  )
}

// ── 子组件：进度卡 ───────────────────────────────────────────────────

function MiniProgress({ label, done, total, color = 'var(--accent-primary)' }: { label: string; done: number; total: number; color?: string }) {
  const pct = total > 0 ? Math.round(done / total * 100) : 0
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600, fontSize: 11 }}>{done}/{total}  {pctStr(pct)}</span>
      </div>
      <div style={s.progressBar}>
        <div style={s.progressFill(pct, color)} />
      </div>
    </div>
  )
}

// ── 子组件：通过率卡 ─────────────────────────────────────────────────

function PassCard({ label, stats, color, onClick }: { label: string; stats: { total: number; passed: number; failed: number; pass_rate: number }; color: string; onClick?: () => void }) {
  return (
    <div style={{ ...s.statCard, textAlign: 'left', ...(onClick ? { cursor: 'pointer' } : {}) }} onClick={onClick}>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>{pctStr(stats.pass_rate)}</div>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
        {stats.passed}/{stats.total} 通过
        {stats.failed > 0 && <span style={{ color: '#f85149' }}> | {stats.failed} 失败</span>}
      </div>
      <div style={s.progressBar}>
        <div style={s.progressFill(stats.pass_rate, color)} />
      </div>
    </div>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const { navigate } = useNavigation()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // modal
  const [showModal, setShowModal] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [form, setForm] = useState({ name: '', key: '', description: '', priority: 'P2', owner_id: '', start_date: '', end_date: '', target_version: '', tags: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // detail modal
  const [detailModal, setDetailModal] = useState<{ title: string; content: React.ReactNode } | null>(null)

  // data fetch
  const fetchProjects = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      if (searchQuery) params.name = searchQuery
      const res = await api.listProjects(params)
      const list = res.data || { items: [], total: 0 }
      setProjects(list.items || [])
    } catch { setError('获取项目列表失败') } finally { setLoading(false) }
  }, [statusFilter, searchQuery])

  useEffect(() => { void fetchProjects() }, [fetchProjects])

  useEffect(() => {
    if (!selectedId) { setProjectDetail(null); return }
    api.getProject(selectedId).then(res => setProjectDetail(res.data || null)).catch(() => setProjectDetail(null))
  }, [selectedId])

  const selectedProject = projects.find(p => p.project_id === selectedId) || null

  const filtered = useMemo(() => {
    let list = projects
    if (searchQuery) { const q = searchQuery.toLowerCase(); list = list.filter(p => p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q)) }
    if (statusFilter) list = list.filter(p => p.status === statusFilter)
    return list
  }, [projects, searchQuery, statusFilter])

  // modal open
  const openCreate = () => { setEditMode(false); setForm({ name: '', key: '', description: '', priority: 'P2', owner_id: '', start_date: '', end_date: '', target_version: '', tags: '' }); setFormError(''); setShowModal(true) }
  const openEdit = () => {
    if (!selectedProject) return
    setEditMode(true)
    setForm({
      name: selectedProject.name, key: selectedProject.key, description: selectedProject.description || '',
      priority: selectedProject.priority || 'P2', owner_id: selectedProject.owner_id || '',
      start_date: selectedProject.start_date ? selectedProject.start_date.slice(0, 10) : '',
      end_date: selectedProject.end_date ? selectedProject.end_date.slice(0, 10) : '',
      target_version: selectedProject.target_version || '',
      tags: selectedProject.tags?.join(', ') || '',
    }); setFormError(''); setShowModal(true)
  }
  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('项目名称不能为空'); return }
    if (!editMode && !form.key.trim()) { setFormError('项目标识不能为空'); return }
    setSaving(true); setFormError('')
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(), key: form.key.trim(), description: form.description.trim() || null,
        priority: form.priority, owner_id: form.owner_id || null,
        start_date: form.start_date ? new Date(form.start_date).toISOString() : null,
        end_date: form.end_date ? new Date(form.end_date).toISOString() : null,
        target_version: form.target_version || null,
        tags: form.tags ? form.tags.split(',').map(s => s.trim()).filter(Boolean) : [],
      }
      if (editMode) { await api.updateProject(selectedId, payload as any) }
      else { await api.createProject(payload as any) }
      setShowModal(false); await fetchProjects()
    } catch (err: unknown) { setFormError(err instanceof Error ? err.message : '保存失败') } finally { setSaving(false) }
  }
  const handleDelete = async () => {
    if (!selectedId || !confirm(`确定删除项目「${selectedProject?.name}」？`)) return
    try { await api.deleteProject(selectedId); setSelectedId(''); await fetchProjects() } catch { setError('删除失败') }
  }
  const handleToggleStatus = async () => {
    if (!selectedId || !selectedProject) return
    const ns = selectedProject.status === 'active' ? 'archived' : 'active'
    try { await api.updateProject(selectedId, { status: ns }); await fetchProjects() } catch { setError('状态更新失败') }
  }

  // stats helpers — 使用 mock 兜底
  const rawStats = projectDetail?.stats as ProjectStats | null
  const stats = useStats(rawStats)
  const taskBreakdown = stats?.task
  const assignees = stats?.assignee_distribution as AssigneeDistribution[] | undefined

  return (
    <div style={s.wrapper}>
      {/* toolbar */}
      <div style={s.toolbar}>
        <input className="form-input" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索项目..." style={{ width: 160, fontSize: 12, padding: '4px 8px' }} />
        {[{ key: '', label: '全部' }, { key: 'active', label: '活跃' }, { key: 'archived', label: '已归档' }].map(f => (
          <button key={f.key} onClick={() => setStatusFilter(f.key)} style={{ padding: '3px 8px', fontSize: 11, border: 'none', borderRadius: 5, cursor: 'pointer', background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)', fontWeight: statusFilter === f.key ? 600 : 400 }}>{f.label}</button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="btn btn--primary btn--sm" onClick={openCreate} style={{ padding: '5px 14px', fontSize: 12 }}>+ 新建</button>
      </div>

      {/* workspace */}
      <div style={s.workspace}>
        <aside style={s.sidePanel}>
          <div style={s.scroll}>
            {loading && <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>加载中...</div>}
            {error && <div style={{ padding: 16, fontSize: 13, color: '#f85149' }}>{error}</div>}
            {!loading && !error && filtered.length === 0 && (
              <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
                {searchQuery || statusFilter ? '无匹配项目' : '暂无项目，点击上方按钮创建'}
              </div>)}
            {filtered.map(p => {
              const meta = STATUS[p.status] || { label: p.status, color: '#8b949e' }
              const prio = PRIORITY[p.priority] || PRIORITY.P2
              const isActive = p.project_id === selectedId
              return (
                <div key={p.project_id} onClick={() => setSelectedId(p.project_id)}
                  style={{ padding: '8px 14px', cursor: 'pointer', borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent', background: isActive ? 'var(--surface-secondary)' : 'transparent', transition: 'background 0.12s' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 1 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                    <span style={s.pill(prio.color + '22', prio.color)}>{prio.label}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span>{p.key}</span>
                    <span style={{ color: meta.color }}>{meta.label}</span>
                    {p.target_version && <span>v{p.target_version}</span>}
                  </div>
                  {p.start_date && p.end_date && (
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{fmtDate(p.start_date)} ~ {fmtDate(p.end_date)}</div>
                  )}
                </div>
              )
            })}
          </div>
        </aside>

        <main style={s.mainPanel}>
          {selectedProject ? (
            <div style={s.detailScroll}>
              {/* header + meta */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <button className="btn btn--ghost btn--sm" onClick={() => setSelectedId('')} style={{ fontSize: 12 }}>← 返回列表</button>
                    <span style={{ fontSize: 16, fontWeight: 700 }}>{selectedProject.name}</span>
                    <span style={s.pill(STATUS[selectedProject.status]?.color + '22', STATUS[selectedProject.status]?.color || '#8b949e')}>{STATUS[selectedProject.status]?.label}</span>
                    <span style={s.pill(PRIORITY[selectedProject.priority]?.color + '22', PRIORITY[selectedProject.priority]?.color || '#8b949e')}>{PRIORITY[selectedProject.priority]?.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 4 }}>
                      {selectedProject.key}
                      {selectedProject.created_by && <> | 创建者：{selectedProject.created_by}</>}
                      {selectedProject.created_at && <> | {fmtDate(selectedProject.created_at)}</>}
                      {selectedProject.owner?.username && <> | 负责人：{selectedProject.owner.username}</>}
                      {selectedProject.target_version && <> | v{selectedProject.target_version}</>}
                    </span>
                  </div>
                  {selectedProject.description && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 0 }}>{selectedProject.description}</div>}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button className="btn btn--ghost btn--sm" onClick={handleToggleStatus} style={{ fontSize: 12 }}>{selectedProject.status === 'active' ? '归档' : '激活'}</button>
                  <button className="btn btn--secondary btn--sm" onClick={openEdit} style={{ fontSize: 12 }}>编辑</button>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete} style={{ fontSize: 12 }}>删除</button>
                </div>
              </div>

              {/* ── 项目进度 + 关联资源 ── */}
              {stats && (
                <div style={{ marginBottom: 14, padding: 14, background: 'var(--surface-primary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                  {/* 标题行：左进度标题 + 右关联资源入口 */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>项目进度</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {[
                        { label: '需求', count: stats.requirement_count, color: '#58a6ff', onClick: () => navigate('requirements') },
                        { label: '手工用例', count: stats.test_case_count, color: '#3fb950', onClick: () => navigate('testCases') },
                        { label: '自动化', count: stats.auto_case_count, color: '#d29922', onClick: () => navigate('testCases') },
                        { label: '计划', count: stats.plan_count, color: '#a371f7', onClick: () => navigate('testPlanStudioDemo') },
                      ].map((item, i) => (
                        <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, padding: '2px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer', background: `${item.color}12`, color: item.color, border: `1px solid ${item.color}25` }}
                          onClick={item.onClick}>
                          {item.label} <span style={{ fontWeight: 700, fontSize: 12 }}>{item.count}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                  {/* 进度条区域 */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    <MiniProgress label="执行任务" done={taskBreakdown?.done || 0} total={taskBreakdown?.total || 0} color="#3fb950" />
                    <MiniProgress label="手工通过率" done={stats.manual_pass.passed} total={stats.manual_pass.total} color="#58a6ff" />
                    <MiniProgress label="自动化通过率" done={stats.auto_pass.passed} total={stats.auto_pass.total} color="#d29922" />
                    <MiniProgress label="需求覆盖率" done={stats.test_case_count} total={stats.requirement_count} color="#a371f7" />
                  </div>
                </div>
              )}

              {/* ── 风险/阻塞项 ── */}
              {mockBlockers.length > 0 && (
                <div style={{ marginBottom: 14, padding: 10, background: '#f851490a', borderRadius: 6, border: '1px solid #f8514920' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: '#f85149' }}>⚠</span>
                    <span style={{ color: 'var(--text-primary)' }}>风险/阻塞项</span>
                    <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: '#a371f722', color: '#a371f7', border: '1px solid #a371f733', letterSpacing: '0.04em' }}>AI</span>
                    <span style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-tertiary)' }}>{mockBlockers.length} 项需关注</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {mockBlockers.map(b => (
                      <span key={b.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 9px', borderRadius: 5, background: '#f8514910', border: '1px solid #f8514925', fontSize: 11 }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: b.color, flexShrink: 0 }} />
                        <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{b.name}</span>
                        <span style={{ color: '#f85149', fontSize: 10 }}>{b.type}</span>
                        <span style={{ color: 'var(--text-tertiary)', fontSize: 10 }}>{b.assignee}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* ── 统计数据 ── */}
              {stats && (
                <div style={{ marginBottom: 14 }}>
                  <SectionHeader title="统计数据" />
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '手工用例列表', content: <CaseDetailTable cases={mockManualCases} type="manual" /> })}>
                      <div style={s.statValue}>{stats.test_case_count}</div>
                      <div style={s.statLabel}>手工用例 →</div>
                    </div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '自动化用例列表', content: <CaseDetailTable cases={mockAutoCases} type="auto" /> })}>
                      <div style={s.statValue}>{stats.auto_case_count}</div>
                      <div style={s.statLabel}>自动化用例 →</div>
                    </div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '测试需求覆盖详情', content: <ReqDetailTable reqs={mockRequirements} /> })}>
                      <div style={s.statValue}>{stats.requirement_count}</div>
                      <div style={s.statLabel}>测试需求 →</div>
                    </div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '执行计划列表', content: <PlanDetailTable plans={mockPlans} /> })}>
                      <div style={s.statValue}>{stats.plan_count}</div>
                      <div style={s.statLabel}>执行计划 →</div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── 通过率 ── */}
              {stats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 14 }}>
                  <PassCard label="手工通过率" stats={stats.manual_pass} color="#58a6ff" onClick={() => setDetailModal({ title: '手工通过率详情', content: <CaseDetailTable cases={mockManualCases.filter(c => c.lastResult !== '未执行')} type="manual" /> })} />
                  <PassCard label="自动化通过率" stats={stats.auto_pass} color="#d29922" onClick={() => setDetailModal({ title: '自动化通过率详情', content: <CaseDetailTable cases={mockAutoCases} type="auto" /> })} />
                  <div style={{ ...s.statCard, textAlign: 'left', cursor: 'pointer' }} onClick={() => setDetailModal({ title: '需求覆盖详情', content: <ReqDetailTable reqs={mockRequirements} /> })}>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>需求覆盖率</div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{pctStr(stats.coverage_rate)}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{stats.test_case_count}用例/{stats.requirement_count}需求</div>
                    <div style={s.progressBar}><div style={s.progressFill(stats.coverage_rate, '#a371f7')} /></div>
                  </div>
                </div>
              )}

              {/* ── 任务细分 ── */}
              {taskBreakdown && (
                <div style={{ marginBottom: 0 }}>
                  <SectionHeader title="任务细分" />
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 14 }}>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '全部任务', content: <TaskDetailTable tasks={mockTasks} /> })}><div style={s.statValue}>{taskBreakdown.total}</div><div style={s.statLabel}>任务总数 →</div></div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '已完成任务', content: <TaskDetailTable tasks={mockTasks.filter(t => t.status === '已完成')} /> })}><div style={{ ...s.statValue, color: '#3fb950' }}>{taskBreakdown.done}</div><div style={s.statLabel}>已完成 →</div></div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '运行中任务', content: <TaskDetailTable tasks={mockTasks.filter(t => t.status === '进行中')} /> })}><div style={{ ...s.statValue, color: '#d29922' }}>{taskBreakdown.running}</div><div style={s.statLabel}>运行中 →</div></div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '失败任务', content: <TaskDetailTable tasks={mockTasks.filter(t => t.status === '失败')} /> })}><div style={{ ...s.statValue, color: '#f85149' }}>{taskBreakdown.failed}</div><div style={s.statLabel}>失败 →</div></div>
                    <div style={{ ...s.statCard, cursor: 'pointer' }} onClick={() => setDetailModal({ title: '待执行任务', content: <TaskDetailTable tasks={mockTasks.filter(t => t.status === '待执行')} /> })}><div style={{ ...s.statValue, color: '#8b949e' }}>{taskBreakdown.pending}</div><div style={s.statLabel}>待执行 →</div></div>
                  </div>
                </div>
              )}

              {/* ── 执行人分布 + 最近动态 ── */}
              {(assignees && assignees.length > 0) || mockActivities.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 12, marginBottom: 14 }}>
                  {/* 左侧：执行人分布（紧凑） */}
                  {assignees && assignees.length > 0 && (
                    <div style={{ background: 'var(--surface-primary)', borderRadius: 6, border: '1px solid var(--border-subtle)', padding: '10px 12px', overflow: 'hidden' }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>执行人分布</div>
                      <div style={{ maxHeight: 200, overflowY: 'auto', paddingRight: 4 }}>
                        {assignees.map((a, i) => {
                          const personTasks = mockTasks.filter(t => t.assignee === a.assignee_name)
                          return (
                            <div key={a.assignee_id || i} style={{ marginBottom: 5, cursor: 'pointer', fontSize: 11 }} onClick={() => personTasks.length > 0 && setDetailModal({ title: `${a.assignee_name} 的任务`, content: <TaskDetailTable tasks={personTasks} /> })}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                                <span style={{ fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.assignee_name || a.assignee_id || '未分配'}</span>
                                <span style={{ color: 'var(--text-tertiary)', flexShrink: 0 }}>{a.done_count}/{a.item_count}</span>
                              </div>
                              <div style={s.progressBar}><div style={s.progressFill(a.progress, '#58a6ff')} /></div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                  {/* 右侧：最近动态（10条） */}
                  {mockActivities.length > 0 && (
                    <div style={{ background: 'var(--surface-primary)', borderRadius: 6, border: '1px solid var(--border-subtle)', padding: '10px 12px', overflow: 'hidden' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>最近动态</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#fff', background: 'var(--accent-primary)', padding: '1px 6px', borderRadius: 4, minWidth: 18, textAlign: 'center' }}>{mockActivities.length}</span>
                      </div>
                      <div style={{ maxHeight: 200, overflowY: 'auto', paddingRight: 4 }}>
                        {mockActivities.map((a, i) => {
                          const dotColor: Record<string, string> = { task_done: '#3fb950', task_running: '#d29922', task_fail: '#f85149', plan_create: '#58a6ff', plan_done: '#8b949e', case_pass: '#a371f7' }
                          return (
                            <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, padding: '4px 0', borderBottom: i < mockActivities.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                              <span style={{ width: 5, height: 5, borderRadius: '50%', background: dotColor[a.type] || '#8b949e', flexShrink: 0 }} />
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', fontSize: 11 }}>{a.user}</span>
                              <span style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap', fontSize: 11 }}>{a.action}</span>
                              <span style={{ color: 'var(--accent-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, fontWeight: 500, fontSize: 11 }}>「{a.target}」</span>
                              <span style={{ color: 'var(--text-tertiary)', fontSize: 10, flexShrink: 0, fontWeight: 500 }}>{a.time}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
              选择一个项目查看详情
            </div>
          )}
        </main>
      </div>

      {/* detail modal */}
      {detailModal && (
        <DetailModal title={detailModal.title} onClose={() => setDetailModal(null)}>
          {detailModal.content}
        </DetailModal>
      )}

      {/* create/edit modal */}
      {showModal && (
        <div style={s.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={{ ...s.modal, width: 540 }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{editMode ? '编辑项目' : '新建项目'}</div>
            {formError && <div style={{ fontSize: 12, color: '#f85149', marginBottom: 12, padding: 8, background: '#f8514911', borderRadius: 6 }}>{formError}</div>}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={labelStyle}>名称 *</label>
                <input className="form-input" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>标识 {editMode ? '' : '*'}</label>
                <input className="form-input" value={form.key} onChange={e => setForm(p => ({ ...p, key: e.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '') }))} disabled={editMode} style={inputStyle} />
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={labelStyle}>描述</label>
                <textarea className="form-input" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={2} style={{ width: '100%', fontSize: 13, padding: '6px 10px', resize: 'vertical' }} />
              </div>
              <div>
                <label style={labelStyle}>优先级</label>
                <select className="form-input" value={form.priority} onChange={e => setForm(p => ({ ...p, priority: e.target.value }))} style={inputStyle}>
                  <option value="P0">P0 - 最高</option>
                  <option value="P1">P1 - 高</option>
                  <option value="P2">P2 - 普通</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>目标版本</label>
                <input className="form-input" value={form.target_version} onChange={e => setForm(p => ({ ...p, target_version: e.target.value }))} placeholder="v1.0.0" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>计划开始</label>
                <input type="date" className="form-input" value={form.start_date} onChange={e => setForm(p => ({ ...p, start_date: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>计划结束</label>
                <input type="date" className="form-input" value={form.end_date} onChange={e => setForm(p => ({ ...p, end_date: e.target.value }))} style={inputStyle} />
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={labelStyle}>标签（逗号分隔）</label>
                <input className="form-input" value={form.tags} onChange={e => setForm(p => ({ ...p, tags: e.target.value }))} placeholder="回归, 冒烟, 合入" style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
              <button className="btn btn--ghost btn--sm" onClick={() => setShowModal(false)} style={{ fontSize: 12, padding: '6px 14px' }}>取消</button>
              <button className="btn btn--primary btn--sm" onClick={() => void handleSave()} disabled={saving} style={{ fontSize: 12, padding: '6px 14px' }}>{saving ? '保存中...' : '保存'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 3 }
const inputStyle: React.CSSProperties = { width: '100%', fontSize: 13, padding: '6px 10px' }
